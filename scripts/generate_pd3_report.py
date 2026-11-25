"""Fill the retained PD3 template and export an unsigned local-evidence PDF.

Requires requirements-docs.txt and LibreOffice. Identity fields stay blank.
The source template is never modified; screenshots are not fabricated.
"""
from copy import deepcopy
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory, gettempdir
from zipfile import ZipFile

from docx import Document
from docx.oxml import OxmlElement
from docx.shared import Inches, RGBColor
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TEMPLATE = DOCS / "PD3-Hardening-Report-Template.docx"
OUTPUT_NAME = "WeFiles-Lastname-Firstname-Section-PD3"


def replace_paragraph(paragraph, text):
    runs = paragraph.runs
    first = runs[0] if runs else paragraph.add_run()
    first.text = text
    first.font.color.rgb = RGBColor(0, 0, 0)
    first.font.italic = False
    for run in runs[1:]:
        run.text = ""


def fill_table(table, rows):
    while len(table.rows) < len(rows):
        table._tbl.append(deepcopy(table.rows[-1]._tr))
    for row, values in zip(table.rows, rows):
        for cell, value in zip(row.cells, values):
            replace_paragraph(cell.paragraphs[0], value)
            for paragraph in cell.paragraphs[1:]:
                replace_paragraph(paragraph, "")
    # Repeat the original header on continuation pages without changing styles.
    header = table.rows[0]._tr.get_or_add_trPr()
    if not header.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblHeader"):
        header.append(OxmlElement("w:tblHeader"))


def test_log_image(log, path):
    # A rendering of captured output, explicitly not a browser/terminal screenshot.
    font_path = next((p for p in (
        Path("/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("/System/Library/Fonts/Menlo.ttc"),
    ) if p.exists()), None)
    font = ImageFont.truetype(str(font_path), 19) if font_path else ImageFont.load_default(size=19)
    lines = ["$ python manage.py test", *log.strip().splitlines()]
    widths = [font.getlength(line) for line in lines]
    image = Image.new("RGB", (max(900, int(max(widths)) + 48), 48 + 29 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        draw.text((24, 22 + index * 29), line, font=font, fill="black")
    image.save(path)


def build(destination):
    log = (DOCS / "pd3/test-results.txt").read_text()
    result = re.search(r"Ran (\d+) tests in ([\d.]+)s", log)
    if not result or "\nOK\n" not in log or "FAILED" in log:
        raise ValueError("The captured complete test run must show a passing result.")
    count, seconds = result.groups()
    document = Document(TEMPLATE)
    tables = document.tables
    fill_table(tables[0], [
        ["System Name", "WeFiles"], ["Student Name", ""], ["Section", ""],
        ["Increment", "Project Development 3 - Hardening of Core Features"],
        ["Core Feature Hardened", "Private file vault and standard account features"],
        ["GitHub Repository", "https://github.com/siiinbad/WeFiles-Jumao-as-Jumao-as-G1"],
        ["Date Submitted", ""],
    ])
    fill_table(tables[1], [
        ["PD2 Issue ID", "Description", "Fix Applied", "Status (Fixed / Open)", "PR Link"],
        ["ISS-01", "Supabase environment is not set up; hosted persistence/storage not verified.",
         "Local native PostgreSQL and private-storage failure/retry tests pass. Cloud credentials and hosted storage acceptance are not available; no cloud resources were created.", "Open", "Not created; GitHub read-only"],
        ["ISS-02", "Required public repository name, merged PR evidence and Render URL are unavailable.",
         "Public repository/name verified on 2026-11-26. Existing PRs #1-3 merged into main. PD3 branches are local only; required PRs into develop and hosted URL remain pending.", "Open", "Existing PD2 PRs: repository /pull/1, /pull/2, /pull/3"],
        ["ISS-03", "Final hosted screenshots and identity/test-account information pending.",
         "Three real local-only test accounts created and tested. Identity fields are blank by user request. Browser capture host is unavailable; hosted accounts/screenshots are not verified.", "Open", "Not created; GitHub read-only"],
        ["ISS-04", "Existing source database/legacy Supabase SQL cannot be reused directly.",
         "Fresh PostgreSQL database is built with the tracked Django migrations. Legacy data conversion needs its own migration design and source data; it is not attempted in this hardening increment.", "Open", "Not applicable; documented limitation"],
    ])
    evidence = [
        (tables[2], [
            "vault/forms.py: FolderForm, UploadForm, FileForm; invalid-input journey tests.",
            "vault/models.py and services.py: valid names, same-owner destinations, folder uniqueness/cycles/depth and upload limits.",
            "vault/views.py: form errors, messages and redirects; stale actions return validation errors.",
            "config/urls.py and accounts/views.py; tests_requests.py custom 404/500 tests with DEBUG=False.",
            "UUID URL converters, resolve_uuid and scoped get_object_or_404; malformed/missing-ID tests.",
        ]),
        (tables[3], [
            "vault/views.py: login_required on each public vault view; direct-view and URL login tests.",
            "role_required accepts Admin/Member and rejects inactive/invalid roles inside each view.",
            "vault/selectors.py and services.py; tests_database.py and tests_requests.py cross-owner GET/POST checks.",
            "Core/account POST forms contain csrf_token; authenticated CSRF rejection tests.",
            "GET renders forms/confirmation only; mutations execute in POST branches; PUT/PATCH/DELETE rejected.",
            "ORM in core paths; fixed health query has no user input; escaped name/description regression test.",
            "config/settings.py loads .env and validates DJANGO_DEBUG; .env remains ignored. Test-only settings use isolated dummy secrets.",
        ]),
        (tables[4], [
            "Folder uniqueness/self-parent and file positive-size constraints; User role/identity constraints tested in PostgreSQL.",
            "Owner FKs CASCADE; parent/folder FKs PROTECT. signals.py queues private bytes cleanup even on account cascades.",
            "vault/services.py: atomic mutations and owner/record locks; rollback test preserves row and private bytes.",
            "Successful POSTs redirect; CRUD and form tests check redirects. This protects browser refresh, not arbitrary POST replay.",
            "vault/selectors.py select_related(owner, folder/parent); list query-count regression with 15 additional files.",
            "confirm_delete.html and confirm=yes POST check; tests ensure GET and unconfirmed POST do not delete.",
        ]),
    ]
    for table, descriptions in evidence:
        for row, description in zip(table.rows[1:], descriptions):
            replace_paragraph(row.cells[1].paragraphs[0], "Done (local)")
            replace_paragraph(row.cells[2].paragraphs[0], description)
    tests = [
        ("test_member_can_complete_file_crud_and_download", "Valid input and complete private-file journey", "Saved records, redirects, matching download"),
        ("test_blank_and_oversized_uploads_show_errors_without_creating_records", "Invalid core input", "Form errors; no file row"),
        ("test_every_vault_endpoint_requires_login", "Anonymous access", "Redirect to login"),
        ("test_other_member_cannot_list_read_download_edit_or_delete", "Cross-owner record IDs", "404/405; record unchanged"),
        ("test_edit_of_deleted_file_reports_validation_error_without_recreating_it", "Stale file edit", "Validation error; row stays deleted"),
        ("test_authenticated_posts_without_csrf_are_blocked", "Authenticated forged POST", "403; record preserved"),
        ("test_unexpected_failure_uses_custom_500_without_exception_message", "Unexpected server exception", "Custom 500; no exception details"),
        ("test_account_cascade_removes_private_bytes_after_commit", "Owner deletion and storage integrity", "Metadata and bytes removed after commit"),
    ]
    fill_table(tables[5], [["No.", "Test Name", "What it checks", "Expected Result", "Pass/Fail"], *[
        [str(index), name, checks, expected, "Pass"] for index, (name, checks, expected) in enumerate(tests, 1)
    ]])
    fill_table(tables[6], [
        ["Branch", "Merged Into", "Pull Request Link", "What it contains"],
        ["fix/pd3-test-runner", "develop (local)", "Not created - GitHub read-only", "8728b49: plain test command, safe database setup, README and CI"],
        ["hardening/pd3-vault-integrity", "develop (local)", "Not created - GitHub read-only", "8083bf9: role/login checks, locks, stale actions, eight service regressions"],
        ["fix/pd3-cascade-cleanup", "develop (local)", "Not created - GitHub read-only", "6bacb64: durable cleanup for cascaded deletions and rollback tests"],
        ["test/pd3-regressions-report", "develop (local)", "Not created - GitHub read-only", "HTTP, constraint, CSRF, escaping, error-page tests and this report"],
        ["develop", "main (not merged)", "Not created - GitHub read-only", "Release remains pending; main is unchanged"],
    ])
    fill_table(tables[7], [
        ["No.", "Task", "Description", "Priority", "Target Increment"],
        ["1", "GitHub workflow", "Publish work branches and merge the required work PRs into develop, then the release PR into main. Requires permission to write to GitHub; retain branches.", "High", "PD3 submission"],
        ["2", "Cloud acceptance", "Configure a separate Supabase project/private bucket and hosting; verify HTTPS, storage persistence and real cloud retries.", "High", "Before hosted release"],
        ["3", "Screenshots and identity", "Capture genuine validation, denied-access and custom-404 browser screenshots plus console output. Fill identity, rename PDF and sign only after review.", "High", "PD3 submission"],
        ["4", "Legacy data", "Keep a fresh migrated database unless a separately reviewed legacy migration is provided.", "Medium", "Before importing old data"],
    ])
    fill_table(tables[8], [
        ["Issue ID", "Description", "Steps to Reproduce", "Severity", "Status / Workaround"],
        ["PD3-01", "Hosted Supabase/Render behavior is not verified.", "Review PD2 ISS-01/02 and cloud settings; no hosted URL is recorded.", "Major", "Open; local native PostgreSQL tests pass"],
        ["PD3-02", "Required remote branch/PR workflow is incomplete.", "Read repository PR history; no PD3 PRs were created in this task.", "Major", "Open; local work branches retained; GitHub read-only"],
        ["PD3-03", "Genuine UI screenshots are unavailable; student identity is blank.", "Browser tool reports no surfaces and unavailable access host.", "Major", "Open; preserve screenshot slots; user requested blank identity"],
        ["PD3-04", "Local development can show debug pages if DJANGO_DEBUG=True.", "Enable development debug mode and request a missing URL.", "Minor", "Use DJANGO_DEBUG=False for acceptance/hosting; custom handlers tested with debug disabled"],
    ])
    fill_table(tables[9], [
        ["Role", "Username / Email", "Password"],
        ["Admin (local evidence only)", "pd3admin / pd3admin@example.test", "PD3-local-demo-only!374"],
        ["Member (local evidence only)", "pd3member / pd3member@example.test", "PD3-local-demo-only!374"],
        ["Member B (local evidence only)", "pd3other / pd3other@example.test", "PD3-local-demo-only!374"],
    ])
    for paragraph in document.paragraphs:
        text = paragraph.text
        if text.startswith("How to use this template:"):
            replace_paragraph(paragraph,
                f"UNSIGNED LOCAL DRAFT - reviewed 2026-11-26. All {count} tests pass on native PostgreSQL. "
                "Done means source and local-test evidence, not hosted verification. GitHub remains read-only. "
                "Student identity and submission fields are intentionally blank; screenshots and remote PRs remain pending.")
        elif text.startswith("Test file location:"):
            replace_paragraph(paragraph, "Test file location: vault/tests.py, tests_database.py, tests_deployment.py, tests_hardening.py, tests_requests.py; accounts/tests/ covers all four standard features.")
        elif text.startswith("Test run result:"):
            replace_paragraph(paragraph, f"Test run result: Ran {count} tests in {seconds}s - OK; no skipped tests. Command: python manage.py test. Runtime: Python 3.14.10, Django 5.2.19, native PostgreSQL 18.6 on Fedora. See docs/pd3/test-results.txt.")
        elif text == "[Screenshot – test output]":
            replace_paragraph(paragraph, "Captured command output below is rendered from the real test log; it is not a terminal screenshot. The requested genuine screenshot remains pending.")
            image_path = destination.parent / "test-log.png"
            test_log_image(log, image_path)
            paragraph.add_run().add_break()
            paragraph.add_run().add_picture(str(image_path), width=Inches(6.4))
        elif text.startswith("[Screenshot 1"):
            replace_paragraph(paragraph, "Screenshot 1 - validation error: pending genuine browser capture. Automated evidence: invalid/oversized uploads and blank folders return errors without saving records.")
        elif text.startswith("[Screenshot 2"):
            replace_paragraph(paragraph, "Screenshot 2 - blocked access: pending genuine browser capture. Automated evidence: another Member receives 404 on file/folder GET and POST; wrong dashboard role receives 403.")
        elif text.startswith("[Screenshot 3"):
            replace_paragraph(paragraph, "Screenshot 3 - custom 404: pending genuine browser capture. Automated evidence: malformed/missing UUID URLs return the custom error page without traceback when DEBUG=False.")
        elif text.startswith("Name:") or text.startswith("Date:"):
            replace_paragraph(paragraph, "Name: " if text.startswith("Name:") else "Date: ")
        elif paragraph.style.name == "Normal" and any(run.font.italic for run in paragraph.runs) and (
            text.startswith(("Copy every", "For each item", "List your Django", "Paste a screenshot", "List every branch", "Paste labeled", "Work still needed", "Known bugs", "One working account"))
        ):
            paragraph._element.getparent().remove(paragraph._element)
    document.add_paragraph("The declaration is intentionally unsigned. These changes are committed locally only; they are not yet reflected in the remote repository. Demo accounts belong only to the temporary local evidence database, not the user's normal or hosted database.")
    document.core_properties.title = "WeFiles PD3 Hardening Report"
    document.core_properties.subject = "Unsigned local verification; remote workflow and browser screenshots pending"
    for paragraph in document.paragraphs:
        if not paragraph.text.strip() or re.match(r"^\d+(?:\.\d+)?[. ]", paragraph.text):
            paragraph.paragraph_format.keep_with_next = True
    document.save(destination)
    # python-docx can reserialize untouched parts. Restore their original bytes
    # so template styles, numbering, settings, footers and opaque parts survive.
    editable = {"word/document.xml", "word/_rels/document.xml.rels", "[Content_Types].xml", "docProps/core.xml"}
    package = destination.read_bytes()
    from io import BytesIO
    with ZipFile(TEMPLATE) as source, ZipFile(BytesIO(package)) as filled, ZipFile(destination, "w") as output:
        for entry in filled.infolist():
            content = source.read(entry.filename) if entry.filename in source.namelist() and entry.filename not in editable else filled.read(entry.filename)
            output.writestr(entry, content)
    return count


def main():
    office = shutil.which("libreoffice") or shutil.which("soffice")
    if not office:
        raise SystemExit("Install LibreOffice and make libreoffice/soffice available on PATH.")
    with TemporaryDirectory(prefix="wefiles-pd3-report-") as temporary:
        folder = Path(temporary)
        docx = folder / f"{OUTPUT_NAME}.docx"
        count = build(docx)
        # Preserve a task-local editable intermediate for render/OOXML QA.
        shutil.copy2(docx, Path(gettempdir()) / f'{OUTPUT_NAME}.docx')
        profile = (folder / "libreoffice-profile").as_uri()
        subprocess.run([office, f"-env:UserInstallation={profile}", "--headless", "--convert-to", "pdf", "--outdir", str(DOCS), str(docx)], check=True)
    output = DOCS / f"{OUTPUT_NAME}.pdf"
    if not output.exists() or output.stat().st_size < 1000:
        raise SystemExit("LibreOffice did not produce the expected PDF.")
    print(f"Saved {output.relative_to(ROOT)} with all template sections and {count} passing tests.")


if __name__ == "__main__":
    main()
