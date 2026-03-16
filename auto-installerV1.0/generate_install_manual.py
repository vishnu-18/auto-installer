# -*- coding: utf-8 -*-
"""Generate Installation Manual PDF for Auto Installer Genius v1.0"""

import os
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.platypus.flowables import Flowable

PAGE_W, PAGE_H = A4

DARK    = colors.HexColor("#1e1e2e")
BLUE    = colors.HexColor("#89b4fa")
GREEN   = colors.HexColor("#a6e3a1")
RED     = colors.HexColor("#f38ba8")
SUBTEXT = colors.HexColor("#45475a")
ROWALT  = colors.HexColor("#eef2ff")
NOTEBG  = colors.HexColor("#fffbe6")
WARNBG  = colors.HexColor("#fff0f0")
GRIDC   = colors.HexColor("#d0d4e8")
WHITE   = colors.white
BLACK   = colors.HexColor("#1e1e2e")


class ScreenshotBox(Flowable):
    def __init__(self, label, width=15*cm, height=5*cm):
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
        cx = self.width / 2
        cy = self.height / 2
        c.setStrokeColor(BLUE)
        c.setLineWidth(1)
        c.rect(cx-30, cy-18, 60, 36, stroke=1, fill=0)
        c.circle(cx, cy, 10, stroke=1, fill=0)
        c.setFillColor(SUBTEXT)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cx, 8, "[ Screenshot: " + self.label + " ]")


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
        spaceBefore=14, spaceAfter=6, leading=20, backColor=DARK, borderPad=8),
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
    "warn": S("warn", fontSize=9, textColor=colors.HexColor("#8b0000"),
        fontName="Helvetica-Bold", leading=13, spaceAfter=4, backColor=WARNBG,
        leftIndent=8, rightIndent=8, borderPad=5),
    "cap":  S("cap", fontSize=8, textColor=SUBTEXT, fontName="Helvetica-Oblique",
        alignment=TA_CENTER, spaceAfter=8),
    "toc":  S("toc", fontSize=10, fontName="Helvetica", leading=20,
        leftIndent=8, textColor=BLACK),
}


def p(text, style="body"):  return Paragraph(text, STYLES[style])
def h1(text):               return Paragraph("  " + text, STYLES["h1"])
def h2(text):               return Paragraph(text, STYLES["h2"])
def h3(text):               return Paragraph(text, STYLES["h3"])
def b(text):                return Paragraph("&bull;  " + text, STYLES["bull"])
def code(text):             return Paragraph(text.replace("\n", "<br/>"), STYLES["code"])
def note(text):             return Paragraph("<i>Note: " + text + "</i>", STYLES["note"])
def warn(text):             return Paragraph("<b>Warning: " + text + "</b>", STYLES["warn"])
def cap(text):              return Paragraph(text, STYLES["cap"])
def sp(n=0.3):              return Spacer(1, n*cm)
def hr():                   return HRFlowable(width="100%", thickness=0.5, color=GRIDC)
def ss(label, h=5):         return ScreenshotBox(label, height=h*cm)
def pb():                   return PageBreak()


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


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK)
    canvas.rect(0, PAGE_H - 1.1*cm, PAGE_W, 1.1*cm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(1.5*cm, PAGE_H - 0.75*cm, "Auto Installer Genius  |  Ver 1.0")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - 1.5*cm, PAGE_H - 0.75*cm, "Installation Manual")
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, PAGE_W, 0.85*cm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.5*cm, 0.28*cm,
        "Copyright 2026 Vishnu Vardhan  |  " + date.today().strftime("%d %b %Y"))
    canvas.drawRightString(PAGE_W - 1.5*cm, 0.28*cm, "Page " + str(doc.page))
    canvas.restoreState()


def cover():
    story = [sp(2.5)]
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
        p("Installation Manual  |  Version 1.0", "cover_type"),
        sp(2)]
    meta = [
        ["Version",    "1.0"],
        ["Date",       date.today().strftime("%d %B %Y")],
        ["Author",     "Vishnu Vardhan"],
        ["Platform",   "Windows 10/11 (local)  to  Ubuntu 20.04 / 22.04 / 24.04 (remote)"],
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


def toc():
    story = [h1("Table of Contents"), sp(0.2)]
    entries = [
        ("1",  "System Requirements"),
        ("2",  "Prerequisites"),
        ("3",  "Downloading the Application"),
        ("4",  "Installing Python Dependencies"),
        ("5",  "Getting a Cerebras API Key"),
        ("6",  "Configuring the API Key"),
        ("7",  "Preparing the Remote Ubuntu Machine"),
        ("8",  "Running the Application"),
        ("9",  "First-Time Setup Checklist"),
        ("10", "Upgrading to a New Version"),
        ("11", "Uninstalling the Application"),
        ("12", "Troubleshooting"),
    ]
    for num, title in entries:
        story.append(Paragraph("<b>" + num + ".</b>  " + title, STYLES["toc"]))
    story.append(pb())
    return story


def sec1():
    reqs = [
        ["Component",       "Minimum Requirement"],
        ["Operating System","Windows 10 or Windows 11 (64-bit)"],
        ["Python",          "3.10 or higher"],
        ["RAM",             "4 GB (8 GB recommended)"],
        ["Disk Space",      "200 MB free (excluding log files)"],
        ["Network",         "Internet access for Cerebras AI API calls"],
        ["Remote Target",   "Ubuntu 20.04 / 22.04 / 24.04 LTS"],
        ["SSH on Remote",   "OpenSSH server running on port 22 (default)"],
        ["Remote User",     "SSH user must have sudo privileges"],
    ]
    return [
        h1("1.  System Requirements"), sp(0.2),
        make_table(reqs, [4.5*cm, 10.5*cm]),
        sp(),
    ]


def sec2():
    return [
        h1("2.  Prerequisites"), sp(0.2),
        p("Before installing Auto Installer Genius, ensure the following are ready:"),
        sp(0.2),
        h2("On your Windows machine:"),
        b("Python 3.10 or higher installed and added to PATH."),
        b("pip (Python package manager) available in the terminal."),
        b("Git installed (optional, for cloning from GitHub)."),
        b("A Cerebras account with an active API key (free tier is sufficient)."),
        sp(0.2),
        h2("On the remote Ubuntu machine:"),
        b("OpenSSH server installed and running."),
        b("The SSH user account must have sudo privileges."),
        b("Network connectivity from your Windows machine to the Ubuntu machine."),
        b("Port 22 open (or your custom SSH port)."),
        sp(0.2),
        note("No additional software needs to be pre-installed on the remote Ubuntu machine. "
             "The application handles everything over SSH."),
        sp(),
    ]


def sec3():
    return [
        h1("3.  Downloading the Application"), sp(0.2),
        h2("Option A  -  Clone from GitHub (recommended)"),
        p("Open a Command Prompt or PowerShell and run:"),
        sp(0.1),
        code("git clone https://github.com/vishnu-18/auto-installer.git\n"
             "cd auto-installer"),
        sp(0.2),
        h2("Option B  -  Download ZIP from GitHub"),
        b("Go to https://github.com/vishnu-18/auto-installer"),
        b("Click the green Code button, then Download ZIP."),
        b("Extract the ZIP to a folder, e.g. F:\\MySws\\auto-installerV1.0\\"),
        sp(0.2),
        p("The application folder should contain these files:"),
        sp(0.1),
        make_table([
            ["File",               "Description"],
            ["main.py",            "Application entry point - run this to start the app."],
            ["gui.py",             "GUI layout and event handlers."],
            ["installer.py",       "Core installation orchestration logic."],
            ["ssh_client.py",      "SSH connection and command execution."],
            ["ai_client.py",       "Cerebras AI API integration."],
            ["config_manager.py",  "Save/load .mc.json configuration files."],
            ["requirements.txt",   "Python package dependencies."],
            [".env.example",       "Template for the .env API key file."],
        ], [4*cm, 11*cm]),
        sp(),
    ]


def sec4():
    pkgs = [
        ["Package",        "Version",  "Purpose"],
        ["paramiko",       ">=3.0",    "SSH connection and SFTP file upload."],
        ["python-dotenv",  ">=1.0",    "Load API keys from the .env file."],
        ["requests",       ">=2.31",   "HTTP calls to the Cerebras AI API."],
        ["tkinter",        "built-in", "GUI framework (included with Python)."],
        ["reportlab",      ">=4.0",    "PDF generation (for manuals only)."],
    ]
    return [
        h1("4.  Installing Python Dependencies"), sp(0.2),
        p("Open a Command Prompt or PowerShell, navigate to the application folder, "
          "and run:"),
        sp(0.1),
        code("pip install -r requirements.txt"),
        sp(0.2),
        p("This installs the following packages:"),
        sp(0.1),
        make_table(pkgs, [3.5*cm, 2.5*cm, 9*cm]),
        sp(0.2),
        p("To verify the installation was successful:"),
        sp(0.1),
        code("python -c \"import paramiko, dotenv, requests; print('All OK')\""),
        sp(0.2),
        note("If you see 'ModuleNotFoundError' for tkinter, reinstall Python and "
             "make sure the 'tcl/tk and IDLE' option is checked during installation."),
        sp(),
    ]


def sec5():
    return [
        h1("5.  Getting a Cerebras API Key"), sp(0.2),
        p("Auto Installer Genius uses the Cerebras AI API to generate and verify "
          "installation commands. A free account gives access to the models used by this app."),
        sp(0.2),
        h2("Steps to get your API key:"),
        b("<b>Step 1:</b> Go to https://cloud.cerebras.ai and sign up for a free account."),
        b("<b>Step 2:</b> Log in and navigate to the <b>API Keys</b> section."),
        b("<b>Step 3:</b> Click <b>Generate New Key</b>."),
        b("<b>Step 4:</b> Copy the key immediately - it will not be shown again."),
        sp(0.2),
        ss("Cerebras cloud dashboard showing API Keys section", 5),
        cap("Fig 5.1 - Cerebras API Keys page (cloud.cerebras.ai)"),
        sp(0.2),
        p("The free tier includes access to:"),
        b("llama3.1-8b  -  smaller, faster model."),
        b("qwen-3-235b-a22b-instruct-2507  -  larger model used by this application."),
        sp(0.2),
        warn("Keep your API key private. Never commit it to version control or share it. "
             "The .gitignore already excludes the .env file."),
        sp(),
    ]


def sec6():
    return [
        h1("6.  Configuring the API Key"), sp(0.2),
        p("There are two ways to add your Cerebras API key to the application:"),
        sp(0.2),

        h2("Option A  -  Via the Settings menu (recommended)"),
        b("Launch the application: python main.py"),
        b("Click <b>Settings</b> in the menu bar."),
        b("Click <b>Environment Variables (.env)...</b>"),
        b("The .env editor opens. Add or update the line:"),
        sp(0.1),
        code("CEREBRAS_API_KEY=csk-xxxxxxxxxxxxxxxxxxxx"),
        sp(0.1),
        b("Click <b>Save</b>. The key is reloaded immediately."),
        sp(0.2),
        ss("Settings menu open with Environment Variables option highlighted", 4),
        cap("Fig 6.1 - Settings menu and .env editor"),
        sp(0.2),

        h2("Option B  -  Edit the .env file directly"),
        p("Copy the .env.example file to .env and edit it:"),
        sp(0.1),
        code("copy .env.example .env\nnotepad .env"),
        sp(0.1),
        p("Set the following values (no quotes around values):"),
        sp(0.1),
        code("CEREBRAS_API_KEY=csk-xxxxxxxxxxxxxxxxxxxx\n"
             "CEREBRAS_MODEL=qwen-3-235b-a22b-instruct-2507"),
        sp(0.2),
        note("The CEREBRAS_MODEL line is optional. If omitted, the app defaults to "
             "qwen-3-235b-a22b-instruct-2507 automatically."),
        sp(),
    ]


def sec7():
    return [
        h1("7.  Preparing the Remote Ubuntu Machine"), sp(0.2),
        p("The target Ubuntu machine needs only OpenSSH server and a sudo-enabled user. "
          "Run these commands directly on the Ubuntu machine (or via any existing SSH session):"),
        sp(0.2),

        h2("7.1  Install and enable SSH server"),
        code("sudo apt-get update\n"
             "sudo apt-get install -y openssh-server\n"
             "sudo systemctl enable ssh\n"
             "sudo systemctl start ssh"),
        sp(0.2),

        h2("7.2  Verify SSH is running"),
        code("sudo systemctl status ssh"),
        sp(0.1),
        p("You should see <b>Active: active (running)</b> in the output."),
        sp(0.2),

        h2("7.3  Ensure the user has sudo privileges"),
        code("# Check current groups\ngroups your_username\n\n"
             "# Add to sudo group if not already there\nsudo usermod -aG sudo your_username"),
        sp(0.2),

        h2("7.4  Find the machine's IP address"),
        code("ip addr show | grep 'inet ' | grep -v 127.0.0.1"),
        sp(0.1),
        p("Note the IP address shown (e.g. 192.168.100.197). "
          "This is what you enter in the <b>Remote IP / Host</b> field."),
        sp(0.2),

        h2("7.5  Test SSH from your Windows machine"),
        p("Open PowerShell and test the connection:"),
        code("ssh your_username@192.168.100.197"),
        sp(0.2),
        note("The application uses SUDO_ASKPASS to handle sudo non-interactively. "
             "No changes to /etc/sudoers are required on the remote machine."),
        sp(),
    ]


def sec8():
    return [
        h1("8.  Running the Application"), sp(0.2),
        p("Navigate to the application folder and run:"),
        sp(0.1),
        code("python main.py"),
        sp(0.2),
        p("The GUI window will open and the application is ready to use."),
        sp(0.2),
        ss("Application main window on first launch", 7),
        cap("Fig 8.1 - Auto Installer Genius on first launch"),
        sp(0.2),

        h2("Optional: Create a desktop shortcut"),
        p("Create a file named <b>AutoInstaller.bat</b> on your desktop:"),
        sp(0.1),
        code("@echo off\ncd /d F:\\MySws\\auto-installerV1.0\npython main.py"),
        sp(0.2),

        h2("Optional: Create a Windows shortcut (.lnk)"),
        b("Right-click the desktop and select New - Shortcut."),
        b("Target: python F:\\MySws\\auto-installerV1.0\\main.py"),
        b("Start in: F:\\MySws\\auto-installerV1.0"),
        b("Name it: Auto Installer Genius"),
        sp(),
    ]


def sec9():
    checklist = [
        ["", "Checklist Item"],
        ["[ ]", "Python 3.10+ installed and accessible via 'python --version'"],
        ["[ ]", "pip install -r requirements.txt completed without errors"],
        ["[ ]", "CEREBRAS_API_KEY set in the .env file"],
        ["[ ]", "SSH server running on the target Ubuntu machine"],
        ["[ ]", "SSH user has sudo privileges on the target machine"],
        ["[ ]", "Network connectivity confirmed (ping or SSH test)"],
        ["[ ]", "Application launches with 'python main.py'"],
        ["[ ]", "Entered host details and clicked Install for a test run"],
        ["[ ]", "Log file created in the logs/ directory after first run"],
    ]
    t = Table(checklist, colWidths=[1*cm, 14*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("TEXTCOLOR",     (0,1), (0,-1), BLUE),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, ROWALT]),
        ("GRID",          (0,0), (-1,-1), 0.5, GRIDC),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("ALIGN",         (0,0), (0,-1), "CENTER"),
    ]))
    return [
        h1("9.  First-Time Setup Checklist"), sp(0.2),
        p("Use this checklist to confirm everything is configured correctly "
          "before your first installation run:"),
        sp(0.2),
        t,
        sp(),
    ]


def sec10():
    return [
        h1("10.  Upgrading to a New Version"), sp(0.2),
        p("To upgrade to a newer version of Auto Installer Genius:"),
        sp(0.2),
        h2("If installed via Git:"),
        code("cd F:\\MySws\\auto-installer\ngit pull origin main"),
        sp(0.2),
        h2("If installed via ZIP download:"),
        b("Download the new ZIP from https://github.com/vishnu-18/auto-installer"),
        b("Extract to a new folder (e.g. auto-installerV1.1)."),
        b("Copy your existing .env file to the new folder."),
        b("Copy your .settings.json file to preserve log path and local package dir settings."),
        b("Copy any saved .mc.json configuration files you want to keep."),
        b("Run pip install -r requirements.txt in the new folder."),
        sp(0.2),
        note("Your .env file, .settings.json, and .mc.json config files are not "
             "overwritten by upgrades. Always back them up before upgrading."),
        sp(),
    ]


def sec11():
    return [
        h1("11.  Uninstalling the Application"), sp(0.2),
        p("Auto Installer Genius does not use a Windows installer. "
          "To remove it, simply delete the application folder:"),
        sp(0.1),
        code("rmdir /s /q F:\\MySws\\auto-installerV1.0"),
        sp(0.2),
        p("To also remove the Python packages installed for this app "
          "(only if not used by other projects):"),
        sp(0.1),
        code("pip uninstall paramiko python-dotenv requests reportlab -y"),
        sp(0.2),
        note("Deleting the folder removes all log files, saved configs, and settings. "
             "Back up anything you want to keep before deleting."),
        sp(),
    ]


def sec12():
    issues = [
        ["Error / Symptom",                  "Likely Cause",                    "Fix"],
        ["ModuleNotFoundError: paramiko",
         "Dependencies not installed",
         "Run: pip install -r requirements.txt"],
        ["ModuleNotFoundError: tkinter",
         "Python installed without tcl/tk",
         "Reinstall Python, tick 'tcl/tk and IDLE' option"],
        ["401 Unauthorized (Cerebras API)",
         "Invalid or missing API key",
         "Check CEREBRAS_API_KEY in .env via Settings menu"],
        ["403 Forbidden (Cerebras API)",
         "API key expired or rate limited",
         "Regenerate key at cloud.cerebras.ai"],
        ["404 Not Found (Cerebras API)",
         "Wrong model name in .env",
         "Set CEREBRAS_MODEL=qwen-3-235b-a22b-instruct-2507"],
        ["Error reading SSH protocol banner",
         "Wrong host/port or SSH not running",
         "Verify IP address and run: sudo systemctl status ssh"],
        ["Authentication failed",
         "Wrong username or password",
         "Double-check credentials in the input fields"],
        ["Connection timed out",
         "Firewall blocking port 22",
         "Allow port 22 in firewall: sudo ufw allow 22"],
        ["bash: syntax error near 'do'",
         "Old ssh_client.py version",
         "Ensure ssh_client.py is the latest version from GitHub"],
        ["sudo: no tty present",
         "SUDO_ASKPASS not set up",
         "Auto-handled on connect - ensure SSH connects successfully first"],
        ["python not recognized",
         "Python not in Windows PATH",
         "Reinstall Python and check 'Add to PATH' during setup"],
    ]
    t = Table(issues, colWidths=[4.2*cm, 4.2*cm, 6.6*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, ROWALT]),
        ("GRID",          (0,0), (-1,-1), 0.5, GRIDC),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return [
        h1("12.  Troubleshooting"), sp(0.2),
        p("If you encounter issues during setup or first run, "
          "refer to the table below:"),
        sp(0.2),
        t,
        sp(0.2),
        h2("Checking the log file for details"),
        p("Every run produces a log file in the logs/ directory. "
          "The log contains the full command history, outputs, and AI verdicts. "
          "Check it first when diagnosing any failure:"),
        sp(0.1),
        code("F:\\MySws\\auto-installerV1.0\\logs\\install_SoftwareName_YYYYMMDD_HHMMSS.log"),
        sp(0.2),
        h2("Getting further help"),
        b("Check the GitHub repository for known issues and updates:"),
        b("https://github.com/vishnu-18/auto-installer"),
        b("Review the User Manual for detailed usage instructions."),
        sp(),
    ]


def build():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        "Auto_Installer_Genius_Installation_Manual_v1.0.pdf")

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=1.8*cm,
        bottomMargin=1.5*cm,
        title="Auto Installer Genius - Installation Manual v1.0",
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

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("Generated: " + out_path)
    return out_path


if __name__ == "__main__":
    build()
