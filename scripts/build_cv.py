#!/usr/bin/env python3
"""Build the public CV PDFs (EN, FR, ES) from cv/CV_<LANG>.md into assets/.

Needs fpdf2 (and optionally PyMuPDF for the sanity check) and the macOS Arial fonts:
    python3 scripts/build_cv.py
"""

import re
import sys
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent

# Section headings in the order they appear in each markdown file:
# summary, skills, experience, education, certifications; plus the PDF title for each.
LANGS = {
    "EN": ["Professional summary", "Technical skills", "Professional experience", "Education", "Certifications"],
    "FR": ["Profil professionnel", "Compétences techniques", "Expérience professionnelle", "Formation", "Certifications"],
    "ES": ["Resumen profesional", "Competencias técnicas", "Experiencia profesional", "Formación académica", "Certificaciones"],
}

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_I = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"
FONT_BI = "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf"

MARGIN = 15  # mm
NAME_SIZE = 20
HEADLINE_SIZE = 9
CONTACT_SIZE = 9
SECTION_SIZE = 13
BODY_SIZE = 10
BODY_LH = 4.2
SKILL_LABEL_W = 54  # mm, approx SPS label column
SKILL_ROW_GAP = 0.2
SECTION_GAP = 1.5

NAVY = (43, 62, 79)
BODY_COLOR = (51, 51, 51)
DATE_COLOR = (126, 126, 140)
CONTACT_MUTED = (84, 84, 84)
UNDERLINE = (238, 238, 238)


def strip_md(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.replace("**", "").replace("*", "").strip()


def parse_links(line: str) -> list:
    """Return list of (text, url_or_none) segments."""
    parts = []
    pos = 0
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line):
        if match.start() > pos:
            parts.append((line[pos : match.start()], None))
        parts.append((match.group(1), match.group(2)))
        pos = match.end()
    if pos < len(line):
        parts.append((line[pos:], None))
    return parts if parts else [(line, None)]


def parse_md(path: Path) -> dict:
    lines = [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()]
    data = {
        "name": "",
        "headline": "",
        "contact_lines": [],
        "summary": "",
        "skills": [],
        "jobs": [],
        "education": [],
        "certifications": [],
    }

    keys = ["summary", "skills", "jobs", "education", "certifications"]
    section = None
    section_index = -1
    current_job = None
    header_done = False

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if line.startswith("# "):
            data["name"] = line[2:].strip()
            continue

        if line.startswith("## "):
            section_index += 1
            section = keys[section_index]
            header_done = True
            current_job = None
            continue

        if not header_done:
            if not data["headline"] and "@" not in line and not line.startswith("["):
                data["headline"] = line
            else:
                data["contact_lines"].append(line)
            continue

        if section == "summary":
            data["summary"] = (data["summary"] + " " + line).strip()
        elif section == "skills":
            match = re.match(r"^\*\*(.+?)\*\*\s*(.+)$", line)
            if match:
                data["skills"].append((match.group(1).rstrip(": "), match.group(2)))
        elif section == "jobs":
            job_match = re.match(r"^\*\*(.+?)\*\*\s*[—\-]\s*\*(.+?)\*$", line)
            if job_match:
                current_job = {
                    "title": job_match.group(1).strip(),
                    "date": job_match.group(2).strip(),
                    "bullets": [],
                }
                data["jobs"].append(current_job)
            elif line.startswith("- ") and current_job is not None:
                current_job["bullets"].append(line[2:])
        elif section == "education":
            edu_match = re.match(r"^\*\*(.+?)\*\*\s*\|\s*(.+?)\s*[—\-]\s*\*(.+?)\*$", line)
            if edu_match:
                data["education"].append(
                    {
                        "degree": edu_match.group(1).strip(),
                        "institution": edu_match.group(2).strip(),
                        "date": edu_match.group(3).strip(),
                    }
                )
        elif section == "certifications" and line.startswith("- "):
            data["certifications"].append(line[2:])

    return data


class SPSCVPDF(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.set_auto_page_break(auto=True, margin=MARGIN)
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.add_font("Arial", "", FONT)
        self.add_font("Arial", "B", FONT_B)
        self.add_font("Arial", "I", FONT_I)
        self.add_font("Arial", "BI", FONT_BI)

    def _centered_line(self, segments, size, default_color=BODY_COLOR, lh=4.0):
        """Render a centered line with optional link segments."""
        total_w = 0
        styled = []
        for text, url in segments:
            if not text:
                continue
            color = default_color
            if "@" in text and url is None and "felipe@henao.me" in text:
                url = "mailto:felipe@henao.me"
            if url:
                color = NAVY
            self.set_font("Arial", "", size)
            styled.append((text, url, color, self.get_string_width(text)))
            total_w += styled[-1][3]

        x_start = self.l_margin + (self.epw - total_w) / 2
        y = self.get_y()
        x = x_start
        for text, url, color, w in styled:
            self.set_xy(x, y)
            self.set_font("Arial", "", size)
            self.set_text_color(*color)
            self.cell(w, lh, text, link=url or "")
            x += w
        self.set_y(y + lh)

    def header_block(self, data):
        self.ln(2)
        self.set_font("Arial", "B", NAME_SIZE)
        self.set_text_color(*NAVY)
        self.cell(0, 8, data["name"], align="C", new_x="LMARGIN", new_y="NEXT")

        if data["headline"]:
            self.set_font("Arial", "", HEADLINE_SIZE)
            self.set_text_color(*CONTACT_MUTED)
            self.multi_cell(0, 4, data["headline"], align="C")
            self.ln(1)

        for contact in data["contact_lines"]:
            segments = parse_links(contact)
            expanded = []
            for text, url in segments:
                if "felipe@henao.me" in text and url is None:
                    before, _, after = text.partition("felipe@henao.me")
                    if before:
                        expanded.append((before, None))
                    expanded.append(("felipe@henao.me", "mailto:felipe@henao.me"))
                    if after:
                        expanded.append((after, None))
                else:
                    expanded.append((text, url))
            self._centered_line(expanded, CONTACT_SIZE, default_color=CONTACT_MUTED, lh=3.8)

        y = self.get_y() + 1.5
        self.set_draw_color(*NAVY)
        self.set_line_width(0.4)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.set_y(y + 3)

    def section_heading(self, title):
        self.ln(SECTION_GAP)
        y = self.get_y()
        self.set_fill_color(*UNDERLINE)
        self.rect(self.l_margin, y, self.epw, 6, style="F")
        self.set_xy(self.l_margin + 1, y + 0.3)
        self.set_font("Arial", "B", SECTION_SIZE)
        self.set_text_color(*NAVY)
        self.cell(0, 5, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.ln(1.8)

    def body_paragraph(self, text):
        self.set_x(self.l_margin)
        self.set_font("Arial", "", BODY_SIZE)
        self.set_text_color(*BODY_COLOR)
        self.multi_cell(self.epw, BODY_LH, strip_md(text), align="L")
        self.ln(1)

    def skill_row(self, label, value):
        y = self.get_y()
        self.set_xy(self.l_margin, y)
        self.set_font("Arial", "B", BODY_SIZE)
        self.set_text_color(*NAVY)
        self.cell(SKILL_LABEL_W, BODY_LH, label + ":", new_x="RIGHT")

        self.set_font("Arial", "", BODY_SIZE)
        self.set_text_color(*BODY_COLOR)
        self.multi_cell(self.epw - SKILL_LABEL_W, BODY_LH, value, align="L")
        self.ln(SKILL_ROW_GAP)

    def title_with_date(self, title, date, bold_title=True):
        date_gap = 4  # mm reserved between title block and date
        y = self.get_y()

        self.set_font("Arial", "I", BODY_SIZE)
        self.set_text_color(*DATE_COLOR)
        date_w = self.get_string_width(date)

        self.set_font("Arial", "B" if bold_title else "", BODY_SIZE)
        self.set_text_color(*BODY_COLOR)
        title_max_w = self.epw - date_w - date_gap

        self.set_xy(self.l_margin, y)
        self.multi_cell(title_max_w, BODY_LH, title, align="L")
        title_bottom_y = self.get_y()

        self.set_xy(self.w - self.r_margin - date_w, y)
        self.set_font("Arial", "I", BODY_SIZE)
        self.set_text_color(*DATE_COLOR)
        self.cell(date_w, BODY_LH, date, align="R")

        self.set_y(max(title_bottom_y, y + BODY_LH))
        self.ln(1)

    def rich_bullet(self, text):
        """Render a bullet with optional **bold lead-in** on the same flow, no overlap."""
        y = self.get_y()
        indent_x = self.l_margin + 7
        max_x = self.w - self.r_margin

        self.set_xy(self.l_margin + 3, y)
        self.set_font("Arial", "", BODY_SIZE)
        self.set_text_color(*BODY_COLOR)
        self.cell(4, BODY_LH, "\u2022")

        self.set_xy(indent_x, y)
        old_left = self.l_margin
        self.set_left_margin(indent_x)
        self.set_x(indent_x)
        parts = re.split(r"(\*\*.*?\*\*)", text)
        for part in parts:
            if not part:
                continue
            bold = part.startswith("**") and part.endswith("**")
            chunk = part[2:-2] if bold else part
            self.set_font("Arial", "B" if bold else "", BODY_SIZE)
            self.set_text_color(*BODY_COLOR)
            words = chunk.split(" ")
            for i, word in enumerate(words):
                token = word if i == len(words) - 1 else word + " "
                if token == "":
                    continue
                width = self.get_string_width(token)
                if self.get_x() + width > max_x and self.get_x() > indent_x:
                    self.ln(BODY_LH)
                    self.set_x(indent_x)
                self.write(BODY_LH, token)

        self.set_left_margin(old_left)
        self.ln(BODY_LH + 0.4)

    def simple_bullet(self, text):
        self.set_x(self.l_margin + 3)
        self.set_font("Arial", "", BODY_SIZE)
        self.set_text_color(*BODY_COLOR)
        self.cell(3, BODY_LH, "\u2022", new_x="RIGHT")
        self.set_x(self.l_margin + 7)
        self.multi_cell(self.epw - 7, BODY_LH, strip_md(text), align="L")
        self.ln(0.5)


def build(lang: str):
    titles = LANGS[lang]
    input_path = ROOT / "cv" / f"CV_{lang}.md"
    output_path = ROOT / "assets" / f"CV_Luis_Felipe_Henao_{lang}.pdf"

    data = parse_md(input_path)
    if not (data["summary"] and data["skills"] and data["jobs"] and data["education"]):
        sys.exit(f"{input_path}: a section did not parse")

    pdf = SPSCVPDF()
    pdf.set_title(f"{data['name'].title()} - CV")
    pdf.set_author(data["name"].title())
    pdf.add_page()

    pdf.header_block(data)

    pdf.section_heading(titles[0])
    pdf.body_paragraph(data["summary"])

    pdf.section_heading(titles[1])
    for label, value in data["skills"]:
        pdf.skill_row(label, value)

    pdf.section_heading(titles[2])
    for job in data["jobs"]:
        pdf.ln(0.5)
        pdf.title_with_date(job["title"], job["date"])
        for bullet in job["bullets"]:
            pdf.rich_bullet(bullet)

    pdf.section_heading(titles[3])
    for item in data["education"]:
        title = f"{item['degree']} | {item['institution']}"
        pdf.title_with_date(title, item["date"], bold_title=False)
        pdf.ln(0.2)

    if data["certifications"]:
        pdf.section_heading(titles[4])
        for cert in data["certifications"]:
            pdf.simple_bullet(cert)

    output_path.parent.mkdir(exist_ok=True)
    pdf.output(str(output_path))

    try:
        import fitz

        doc = fitz.open(str(output_path))
        links = [link for page in doc for link in page.get_links()]
        print(f"{output_path.name}: {len(doc)} page(s), {len(links)} link(s)")
    except ImportError:
        print(f"Generated: {output_path}")


if __name__ == "__main__":
    for code in sys.argv[1:] or LANGS:
        build(code.upper())
