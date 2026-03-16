# -*- coding: utf-8 -*-
"""Generate User Manual PDF for Auto Installer Genius v1.0"""

import os
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable

PAGE_W, PAGE_H = A4

# Colours
DARK    = colors.HexColor("#1e1e2e")
BLUE    = colors.HexColor("#89b4fa")
GREEN   = colors.HexColor("#a6e3a1")
RED     = colors.HexColor("#f38ba8")
YELLOW  = colors.HexColor("#f9e2af")
ORANGE  = colors.HexColor("#fab387")
SUBTEXT = colors.HexColor("#45475a")
ROWALT  = colors.HexColor("#eef2ff")
NOTEBG  = colors.HexColor("#fffbe6")
GRIDC   = colors.HexColor("#d0d4e8")
WHITE   = colors.white
BLACK   = colors.HexColor("#1e1e2e")


# ---------------------------------------------------------------------------
# Screenshot placeholder
# ---------------------------------------------------------------------------
class ScreenshotBox(Flowable):
    def __init__(self, label, width=15*cm, height=6*cm):
        super().__init__()
        self.label  = label
        self.width  = width
        self.height = height

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor("#f0f4ff"))
        c.setStrokeColor(BLUE)
        c.setLineWidth(1.2)
        c.setDash(4, 3)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=1)
        c.setDash()
        cx = self.width  / 2
        cy = self.height / 2
        c.setStrokeColor(BLUE)
        c.setLineWidth(1)
        c.rect(cx-30, cy-18, 60, 36, stroke=1, fill=0)
        c.circle(cx, cy, 10, stroke=1, fill=0)
        c.setFillColor(SUBTEXT)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cx, 8, "[ Screenshot: " + self.label + " ]")


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
def S(name, **kw):
    return ParagraphStyle(name, **kw)

STYLES = {
    "cover_title": S("cover_title", fontSize=28, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4, leading=34),
    "cover_sub":   S("cover_sub", fontSize=13, textColor=SUBTEXT,
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4),
    "cover_type":  S("cover_type", fontSize=16, textColor=BLUE,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4),
    "h1":  S("h1", fontSize=14, textColor=WHITE, fontName="Helvetica-Bold",
        spaceBefore=14, spaceAfter=6, leading=20,
        backColor=DARK, leftIndent=0, borderPad=8),
    "h2":  S("h2", fontSize=12, textColor=DARK, fontName="Helvetica-Bold",
        spaceBefore=10, spaceAfter=4),
    "h3":  S("h3", fontSize=10, textColor=SUBTEXT, fontName="Helvetica-Bold",
        spaceBefore=6, spaceAfter=3),
    "body": S("body", fontSize=10, textColor=BLACK, fontName="Helvetica",
        leading=15, spaceAfter=4, alignment=TA_JUSTIFY),
    "bull": S("bull", fontSize=10, textColor=BLACK, fontName="Helvetica",
        leading=15, spaceAfter=3, leftIndent=14, bulletIndent=4),
    "code": S("code", fontSize=9, textColor=WHITE, fontName="Courier",
        leading=13, spaceAfter=4, backColor=DARK,
        leftIndent=8, rightIndent=8, borderPad=6),
    "note": S("note", fontSize=9, textColor=BLACK, fontName="Helvetica-Oblique",
        leading=13, spaceAfter=4, backColor=NOTEBG,
        leftIndent=8, rightIndent=8, borderPad=5),
    "cap":  S("cap", fontSize=8, textColor=SUBTEXT, fontName="Helvetica-Oblique",
        alignment=TA_CENTER, spaceAfter=8),
    "toc":  S("toc", fontSize=10, fontName="Helvetica", leading=20,
        leftIndent=8, textColor=BLACK),
}


def p(text, style="body"):   return Paragraph(text, STYLES[style])
def h1(text):                return Paragraph("  " + text, STYLES["h1"])
def h2(text):                return Paragraph(text, STYLES["h2"])
def h3(text):                return Paragraph(text, STYLES["h3"])
def b(text):                 return Paragraph("&bull;  " + text, STYLES["bull"])
def code(text):              return Paragraph(text.replace("\n","<br/>"), STYLES["code"])
def note(text):              return Paragraph("<i>Note: " + text + "</i>", STYLES["note"])
def cap(text):               return Paragraph(text, STYLES["cap"])
def sp(n=0.3):               return Spacer(1, n*cm)
def hr():                    return HRFlowable(width="100%", thickness=0.5, color=GRIDC)
def ss(label, h=6):          return ScreenshotBox(label, height=h*cm)
def pb():                    return PageBreak()


# ---------------------------------------------------------------------------
# Table helper
# ---------------------------------------------------------------------------
def make_table(data, col_widths, header=True):
    t = Table(data, colWidths=col_widths)
    style = [
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 9.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, ROWALT]),
        ("GRID",          (0,0), (-1,-1), 0.5, GRIDC),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]
    if header:
        style += [
            ("BACKGROUND", (0,0), (-1,0), DARK),
            ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


# ---------------------------------------------------------------------------
# Header / Footer
# ---------------------------------------------------------------------------
def on_page(canvas, doc):
    canvas.saveState()
    # Header
    canvas.setFillColor(DARK)
    canvas.rect(0, PAGE_H - 1.1*cm, PAGE_W, 1.1*cm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(1.5*cm, PAGE_H - 0.75*cm, "Auto Installer Genius  |  Ver 1.0")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - 1.5*cm, PAGE_H - 0.75*cm, "User Manual")
    # Footer
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, PAGE_W, 0.85*cm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.5*cm, 0.28*cm,
        "Copyright 2026 Vishnu Vardhan  |  " + date.today().strftime("%d %b %Y"))
    canvas.drawRightString(PAGE_W - 1.5*cm, 0.28*cm, "Page " + str(doc.page))
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------
def cover():
    story = [sp(2.5)]
    # Title block
    title_data = [[p("Auto Installer Genius", "cover_title")]]
    t = Table(title_data, colWidths=[16*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 20),
        ("BOTTOMPADDING", (0,0), (-1,-1), 20),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
    ]))
    story += [t, sp(0.4),
        p("Automated Remote Software Installation Tool", "cover_sub"),
        HRFlowable(width="100%", thickness=2, color=BLUE),
        sp(0.3),
        p("User Manual  |  Version 1.0", "cover_type"),
        sp(2)]

    meta = [
        ["Version",    "1.0"],
        ["Date",       date.today().strftime("%d %B %Y")],
        ["Author",     "Vishnu Vardhan"],
        ["Platform",   "Windows (local)  to  Ubuntu 22.04 (remote via SSH)"],
        ["AI Engine",  "Cerebras  |  qwen-3-235b-a22b-instruct-2507"],
        ["Repository", "https://github.com/vishnu-18/auto-installer"],
    ]
    t2 = Table(meta, colWidths=[3.5*cm, 12*cm])
    t2.setStyle(TableStyle([
        ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("TEXTCOLOR",     (0,0), (0,-1), SUBTEXT),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [WHITE, ROWALT]),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("GRID",          (0,0), (-1,-1), 0.5, GRIDC),
    ]))
    story += [t2, pb()]
    return story


# ---------------------------------------------------------------------------
# Table of Contents
# ---------------------------------------------------------------------------
def toc():
    story = [h1("Table of Contents"), sp(0.2)]
    entries = [
        ("1",  "Overview"),
        ("2",  "Application Layout"),
        ("3",  "Input Fields"),
        ("4",  "Installing Software"),
        ("5",  "Uninstalling Software"),
        ("6",  "Monitoring Progress"),
        ("7",  "Pausing and Resuming"),
        ("8",  "Cancelling an Installation"),
        ("9",  "File Menu  -  Saving and Loading Configurations"),
        ("10", "Settings Menu"),
        ("11", "Log Files"),
        ("12", "Buttons Reference"),
        ("13", "Understanding AI Verdicts"),
        ("14", "Tips and Best Practices"),
    ]
    for num, title in entries:
        story.append(Paragraph(
            "<b>" + num + ".</b>  " + title, STYLES["toc"]))
    story.append(pb())
    return story


# ---------------------------------------------------------------------------
# Section 1 - Overview
# ---------------------------------------------------------------------------
def sec1():
    return [
        h1("1.  Overview"), sp(0.2),
        p("Auto Installer Genius is a Windows desktop application that automates "
          "the installation and removal of software on remote Ubuntu machines via SSH. "
          "It uses the Cerebras AI API to intelligently generate shell commands, "
          "verify their success, and automatically fix failures without any manual intervention."),
        sp(0.2), h2("Key Features"),
        b("AI-powered command generation using Cerebras (qwen-3-235b model)."),
        b("Automatic SSH connection with non-interactive sudo support."),
        b("Pre-flight check - detects if software is already or partially installed."),
        b("Automatic cleanup of partial installations before a fresh install."),
        b("Real-time execution log with colour-coded output."),
        b("AI verification of every command - auto-fix and retry on failure."),
        b("Install, Uninstall, Pause, Resume, Cancel, and Terminate controls."),
        b("Save and load connection configurations (.mc.json files)."),
        b("Local package upload - install from local files instead of downloading."),
        b("Configurable log file directory."),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 2 - Application Layout
# ---------------------------------------------------------------------------
def sec2():
    layout_rows = [
        ["Section",        "Description"],
        ["Input Panel",    "Enter software name, remote host IP, username, and password."],
        ["Control Buttons","Install, Uninstall, Pause, Resume, Cancel, Quit, Terminate."],
        ["Progress Bar",   "Shows real-time progress: X / N commands completed."],
        ["Execution Log",  "Scrollable log of all commands, outputs, and AI verdicts."],
    ]
    return [
        h1("2.  Application Layout"), sp(0.2),
        ss("Full application main window", 8),
        cap("Fig 2.1 - Auto Installer Genius main window"),
        sp(0.2),
        p("The application window has four main sections:"),
        sp(0.1),
        make_table(layout_rows, [4*cm, 11*cm]),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 3 - Input Fields
# ---------------------------------------------------------------------------
def sec3():
    fields = [
        ["Field",            "Description",                              "Example"],
        ["Software Name",    "Name of the software to install/uninstall","New Relic"],
        ["Remote IP / Host", "IP address or hostname of target machine", "192.168.100.197"],
        ["Username",         "SSH login user (must have sudo access)",   "ubuntu"],
        ["Password",         "SSH login password",                       "**********"],
    ]
    return [
        h1("3.  Input Fields"), sp(0.2),
        p("Fill in all four fields before clicking Install or Uninstall:"),
        sp(0.1),
        make_table(fields, [3.5*cm, 7*cm, 4.5*cm]),
        sp(0.2),
        ss("Input panel with all fields filled in", 4),
        cap("Fig 3.1 - Input panel with connection details entered"),
        sp(0.2),
        note("The remote OS is detected automatically after SSH connects. "
             "You do not need to specify it manually."),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 4 - Installing Software
# ---------------------------------------------------------------------------
def sec4():
    steps = [
        ["Step", "Action"],
        ["1",  "Fill in all four fields in the Input Panel."],
        ["2",  "Click the green Install button."],
        ["3",  "The app connects via SSH and detects the remote OS."],
        ["4",  "Stale apt sources (elastic, newrelic) are cleaned up automatically."],
        ["5",  "Pre-flight check runs - AI determines if software is already installed."],
        ["6",  "If partially installed, a cleanup runs before the fresh install."],
        ["7",  "AI generates the full list of installation commands."],
        ["8",  "Each command is executed on the remote machine one by one."],
        ["9",  "After each command, AI verifies success or failure."],
        ["10", "On failure - AI generates fix commands and retries."],
        ["11", "On fix failure - AI tries a completely different approach."],
        ["12", "A success dialog appears when all commands complete."],
    ]
    return [
        h1("4.  Installing Software"), sp(0.2),
        p("To install software on the remote machine:"),
        sp(0.1),
        b("<b>Step 1:</b> Fill in all four fields in the Input Panel."),
        b("<b>Step 2:</b> Click the green <b>Install</b> button."),
        b("<b>Step 3:</b> Watch the Execution Log for real-time progress."),
        b("<b>Step 4:</b> A success dialog appears when installation completes."),
        sp(0.2),
        p("The application performs these steps automatically in the background:"),
        sp(0.1),
        make_table(steps, [1.2*cm, 13.8*cm]),
        sp(0.2),
        ss("Execution log during active installation showing commands and AI verdicts", 7),
        cap("Fig 4.1 - Execution log during installation"),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 5 - Uninstalling
# ---------------------------------------------------------------------------
def sec5():
    return [
        h1("5.  Uninstalling Software"), sp(0.2),
        p("To completely remove software from the remote machine:"),
        sp(0.1),
        b("<b>Step 1:</b> Fill in the Software Name, Host, Username, and Password."),
        b("<b>Step 2:</b> Click the orange <b>Uninstall</b> button."),
        b("<b>Step 3:</b> Confirm the dialog - 'This will completely uninstall...'"),
        b("<b>Step 4:</b> The app connects, fixes apt sources, then asks AI for uninstall commands."),
        b("<b>Step 5:</b> Each uninstall command is executed and AI-verified."),
        b("<b>Step 6:</b> A success dialog confirms the software has been removed."),
        sp(0.2),
        ss("Uninstall confirmation dialog", 3.5),
        cap("Fig 5.1 - Uninstall confirmation dialog"),
        sp(0.2),
        note("The Uninstall flow asks the AI for commands based on the software name alone. "
             "It does not require a prior installation history in the current session."),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 6 - Monitoring Progress
# ---------------------------------------------------------------------------
def sec6():
    colours = [
        ["Log Colour", "Meaning"],
        ["Yellow",  "Command being executed  (lines starting with >>>)"],
        ["Green",   "Success message or AI SUCCESS verdict"],
        ["Red",     "Failure message or AI FAILURE verdict"],
        ["Blue",    "Info messages: Connecting, AI asking, Detected OS, etc."],
        ["White",   "Raw command output from the remote machine"],
    ]
    return [
        h1("6.  Monitoring Progress"), sp(0.2),
        p("The Progress section shows a progress bar and a command counter "
          "(e.g. 3 / 8 commands). The Execution Log uses colour coding to make "
          "it easy to follow what is happening:"),
        sp(0.1),
        make_table(colours, [3*cm, 12*cm]),
        sp(0.2),
        ss("Progress bar and execution log with colour-coded output", 6),
        cap("Fig 6.1 - Progress bar and colour-coded execution log"),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 7 - Pause / Resume
# ---------------------------------------------------------------------------
def sec7():
    return [
        h1("7.  Pausing and Resuming"), sp(0.2),
        p("Click the yellow <b>Pause</b> button at any time during installation "
          "to pause after the current command finishes. "
          "The button label changes to <b>Resume</b>."),
        sp(0.1),
        p("Click <b>Resume</b> to continue from where it left off."),
        sp(0.2),
        ss("Pause button active during installation", 3.5),
        cap("Fig 7.1 - Pause button during an active installation"),
        sp(0.2),
        note("Pause takes effect after the currently running command and its AI "
             "verification finish. It does not interrupt a command mid-execution."),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 8 - Cancelling
# ---------------------------------------------------------------------------
def sec8():
    return [
        h1("8.  Cancelling an Installation"), sp(0.2),
        p("Click the red <b>Cancel</b> button to abort the installation. "
          "The application will:"),
        sp(0.1),
        b("Wait for the current command to finish."),
        b("Ask the AI for uninstall/rollback commands based on what was already executed."),
        b("Run the rollback commands to clean up the partial installation."),
        b("Show status as 'Cancelling - Uninstalling...' during rollback."),
        sp(0.2),
        ss("Cancel confirmation dialog", 3),
        cap("Fig 8.1 - Cancel confirmation dialog"),
        sp(0.2),
        note("Cancel is a graceful rollback. "
             "Use the red <b>Terminate</b> button only for an emergency hard stop - "
             "it exits immediately without any cleanup or rollback."),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 9 - File Menu
# ---------------------------------------------------------------------------
def sec9():
    fmenu = [
        ["Menu Item",              "Shortcut",       "Description"],
        ["New",                    "Ctrl+N",          "Clear all fields and start fresh."],
        ["Open...",                "Ctrl+O",          "Load a saved .mc.json configuration file."]
,
        ["Save",                   "Ctrl+S",          "Save current fields to the current file."],
        ["Save As...",             "Ctrl+Shift+S",    "Save to a new .mc.json file."],
        ["Recent Configurations",  "-",               "Quick-open recently used config files."],
        ["Quit",                   "-",               "Exit the app (waits for current command)."],
    ]
    return [
        h1("9.  File Menu  -  Saving and Loading Configurations"), sp(0.2),
        p("Connection details can be saved to <b>.mc.json</b> configuration files "
          "so you do not have to re-enter them each time."),
        sp(0.2),
        ss("File menu open showing New, Open, Save, Recent options", 5),
        cap("Fig 9.1 - File menu"),
        sp(0.2),
        make_table(fmenu, [4*cm, 3.5*cm, 7.5*cm]),
        sp(0.2),
        note("Passwords are base64-encoded in saved config files. "
             "Do not share .mc.json files that contain credentials."),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 10 - Settings Menu
# ---------------------------------------------------------------------------
def sec10():
    return [
        h1("10.  Settings Menu"), sp(0.2),
        p("The Settings menu has three options:"),
        sp(0.2),

        h2("10.1  Environment Variables (.env)"),
        p("Opens a text editor showing the contents of the .env file. "
          "Edit your Cerebras API key and other variables here, then click <b>Save</b>. "
          "The file is reloaded immediately - no restart required."),
        sp(0.2),
        ss("Environment Variables editor dialog with Save and Cancel buttons", 5),
        cap("Fig 10.1 - .env editor dialog"),
        sp(0.3),

        h2("10.2  Log File Path"),
        p("Choose the directory where installation log files are saved. "
          "Click <b>Browse...</b> to pick a folder, then <b>Save</b>. "
          "The setting persists across sessions in .settings.json."),
        sp(0.2),
        ss("Log File Path dialog with Browse button", 3.5),
        cap("Fig 10.2 - Log File Path configuration dialog"),
        sp(0.3),

        h2("10.3  Local Package Directory"),
        p("If you have package files already downloaded on your Windows machine "
          "(e.g. .deb files, .tar.gz archives), set this directory path here. "
          "When set, all files in that directory are uploaded to the remote machine "
          "via SFTP before installation begins. "
          "The AI is then instructed to use those local files instead of downloading."),
        sp(0.2),
        ss("Local Package Directory dialog with Browse and Clear buttons", 4),
        cap("Fig 10.3 - Local Package Directory configuration dialog"),
        sp(0.2),
        note("Leave Local Package Directory empty to use the default behaviour "
             "where the AI downloads packages from the internet on the remote machine. "
             "Click Clear to reset it."),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 11 - Log Files
# ---------------------------------------------------------------------------
def sec11():
    return [
        h1("11.  Log Files"), sp(0.2),
        p("Every install and uninstall operation is automatically saved to a log file. "
          "Log files are named:"),
        sp(0.1),
        code("install_SoftwareName_YYYYMMDD_HHMMSS.log"),
        sp(0.2),
        p("Default location:"),
        code("F:\\MySws\\auto-installerV1.0\\logs\\"),
        sp(0.2),
        p("Each log file contains:"),
        b("Full path and timestamp of the log file."),
        b("Software name, host, and start time."),
        b("All AI-generated commands (numbered list)."),
        b("Raw output from each command on the remote machine."),
        b("AI verdict for each command (SUCCESS / FAILURE + reason)."),
        b("Fix commands and alternative commands if triggered."),
        b("End timestamp."),
        sp(0.2),
        note("Change the log directory via Settings - Log File Path. "
             "The directory is created automatically if it does not exist."),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 12 - Buttons Reference
# ---------------------------------------------------------------------------
def sec12():
    buttons = [
        ["Button",       "Colour",     "State",    "Description"],
        ["Install",      "Green",      "Always",   "Start installation of the specified software."],
        ["Uninstall",    "Orange",     "Always",   "Completely remove the specified software."],
        ["Pause",        "Yellow",     "Running",  "Pause after the current command finishes."],
        ["Resume",       "Yellow",     "Paused",   "Continue a paused installation."],
        ["Cancel",       "Red",        "Running",  "Abort and rollback via AI-assisted uninstall."],
        ["Quit",         "Gray",       "Always",   "Exit app gracefully (waits for current command)."],
        ["Terminate",    "Bright Red", "Always",   "Emergency hard exit - no cleanup, immediate."],
    ]
    return [
        h1("12.  Buttons Reference"), sp(0.2),
        make_table(buttons, [2.8*cm, 2.2*cm, 2.2*cm, 7.8*cm]),
        sp(0.2),
        ss("Control buttons bar showing all buttons", 2.5),
        cap("Fig 12.1 - Control buttons bar"),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 13 - AI Verdicts
# ---------------------------------------------------------------------------
def sec13():
    verdicts = [
        ["Verdict",      "Meaning",                              "What Happens Next"],
        ["SUCCESS",      "Command completed as expected.",        "Move to the next command."],
        ["FAILURE",      "Command failed or produced errors.",    "AI generates fix commands."],
        ["Fix SUCCESS",  "Fix commands resolved the issue.",      "Re-run or skip original command."],
        ["Fix FAILURE",  "Fix commands also failed.",             "AI tries alternative approach."],
        ["Alt FAILURE",  "All approaches failed.",                "Installation aborted (FAILED)."],
    ]
    return [
        h1("13.  Understanding AI Verdicts"), sp(0.2),
        p("After each command executes, the AI analyses the output and exit code "
          "to determine if it succeeded. The verdict appears in the log as:"),
        sp(0.1),
        code("AI verdict: SUCCESS - The package was installed successfully.\n"
             "AI verdict: FAILURE - apt-get returned a non-zero exit code."),
        sp(0.2),
        make_table(verdicts, [2.8*cm, 5.5*cm, 6.7*cm]),
        sp(0.2),
        p("The AI also short-circuits verification for idempotent results. "
  
          "If the output contains phrases like 'already installed', "
          "'already the newest version', or 'nothing to do', "
          "it is automatically marked as SUCCESS without an API call."),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Section 14 - Tips
# ---------------------------------------------------------------------------
def sec14():
    return [
        h1("14.  Tips and Best Practices"), sp(0.2),
        b("Always test with a non-production VM before running on live servers."),
        b("Save your connection config (File - Save) to avoid re-entering details each time."),
        b("Check the log file after each run - it contains the full command history."),
        b("If installation fails, the log shows exactly which command failed and why."),
        b("Use the Local Package Directory setting for environments where the remote "
          "machine has no internet access."),
        b("The Cerebras free tier supports two models. The app uses the larger "
          "qwen-3-235b model for better command accuracy."),
        b("Rotate your Cerebras API key periodically and update it via "
          "Settings - Environment Variables."),
        b("Never share your .env file or .mc.json config files containing passwords."),
        b("Use Pause if you need to inspect the remote machine mid-installation."),
        b("Use Terminate only as a last resort - it does not clean up partial installs."),
        sp(),
    ]


# ---------------------------------------------------------------------------
# Build and write PDF
# ---------------------------------------------------------------------------
def build():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "Auto_Installer_Genius_User_Manual_v1.0.pdf")

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=1.8*cm,
        bottomMargin=1.5*cm,
        title="Auto Installer Genius - User Manual v1.0",
        author="Vishnu Vardhan",
    )

    story = []
    story += cover()
    story += toc()
    story += sec1()
    story += sec2()
    story += sec3()
    story += sec4()
    story += sec5()
    story += sec6()
    story += sec7()
    story += sec8()
    story += sec9()
    story += sec10()
    story += sec11()
    story += sec12()
    story += sec13()
    story += sec14()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("Generated: " + out_path)
    return out_path


if __name__ == "__main__":
    build()
