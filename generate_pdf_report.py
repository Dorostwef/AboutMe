import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Preformatted
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (on pages after the first page)
        if self._pageNumber > 1:
            self.drawString(54, letter[1] - 36, "Sharif University of Technology | CE4051 AI-Native Systems Design — Assignment 1")
            self.drawRightString(letter[0] - 54, letter[1] - 36, "Amirreza Dorosti (403110466)")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)
            
        # Footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawString(54, 36, "AboutMe AI-Native Portfolio — Final Submission Report")
        self.drawRightString(letter[0] - 54, 36, page_str)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 46, letter[0] - 54, 46)
        self.restoreState()

def build_pdf(filename="AboutMe_Submission_Amirreza_Dorosti_403110466.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#334155"),
        spaceAfter=12
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3.5
    )

    code_style = ParagraphStyle(
        'CodeText',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a")
    )
    
    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1: COVER & SECTION 1 (Hamravesh Deployment & Steps)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("AboutMe: AI-Native Personal Portfolio", title_style))
    story.append(Paragraph("Sharif University of Technology — CE4051: AI-Native Systems Design (Fall 2026)", subtitle_style))
    
    meta_data = [
        [
            Paragraph("<b>Author:</b> Amirreza Dorosti", body_style),
            Paragraph("<b>Student ID:</b> 403110466", body_style)
        ],
        [
            Paragraph("<b>Public App (Hamravesh):</b> <font color='#1d4ed8'><u>https://aboutdorost.darkube.ir</u></font>", body_style),
            Paragraph("<b>GitHub Repository:</b> <font color='#1d4ed8'><u>https://github.com/Dorostwef/AboutMe</u></font>", body_style)
        ],
        [
            Paragraph("<b>Hosting Platform:</b> Hamravesh Darkube PaaS", body_style),
            Paragraph("<b>Core Stack:</b> FastAPI, Uvicorn, Docker, AsyncOpenAI", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[260, 244])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Public Address & Deployment on Hamravesh Darkube", h1_style))
    story.append(Paragraph(
        "The application is fully containerized, automated, and running live on <b>Hamravesh Darkube</b> at: "
        "<font color='#1d4ed8'><b>https://aboutdorost.darkube.ir</b></font>. "
        "The complete source repository is hosted on GitHub at: <font color='#1d4ed8'><b>https://github.com/Dorostwef/AboutMe</b></font>.",
        body_style
    ))
    story.append(Paragraph("<b>Commands & Deployment Lifecycle Steps:</b>", h2_style))
    
    steps = [
        "<b>1. Container Packaging (Dockerfile):</b> Created a single-stage, hardened <code>python:3.11-slim</code> container image. All dependencies are cached via <code>pip install --no-cache-dir -r requirements.txt</code>. The service exposes port <code>8000</code> and executes via <code>uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}</code>.",
        "<b>2. Git Repository & Source Management:</b> Synced the repository structure to GitHub using:<br/>"
        "<code>git remote add origin git@github.com:Dorostwef/AboutMe.git<br/>git push -u origin main</code>",
        "<b>3. App Creation on Hamravesh Darkube:</b> In the Hamravesh web console (<code>console.hamravesh.com</code>), created a new application under <i>Darkube</i> connected to <code>Dorostwef/AboutMe</code> with auto-build triggers on git commit push.",
        "<b>4. Environment Variable Configuration:</b> In the app's environment configuration tab, set the primary universal parameters:<br/>"
        "• <code>API_KEY</code>: Active API authentication token (OpenRouter / provider key).<br/>"
        "• <code>URL</code>: Endpoint URL (e.g. <code>https://openrouter.ai/api/v1</code> or custom endpoint).<br/>"
        "• <code>MODEL</code>: Model identifier (<code>meta-llama/llama-3.3-70b-instruct</code>).<br/>"
        "• <code>GITHUB_TOKEN</code>: Personal access token (raises rate limit to 5,000 req/hr).<br/>"
        "• <code>PORT=8000</code>: Inbound HTTP container port.",
        "<b>5. Domain & Ingress Routing:</b> Assigned the custom domain <code>aboutdorost.darkube.ir</code> to the service, routing HTTP/HTTPS traffic directly to container port 8000 with automated Let's Encrypt TLS certificate provisioning.",
        "<b>6. Runtime Health Probing:</b> Integrated health endpoint at <code>https://aboutdorost.darkube.ir/api/health</code> returning HTTP 200 with active provider and loaded record metadata."
    ]
    for step in steps:
        story.append(Paragraph(f"• {step}", bullet_style))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2: SECTION 2 (JSON Schema, Record & Visibility Control)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. JSON Profile Schema, Record & Access Control", h1_style))
    story.append(Paragraph(
        "All facts known to the assistant are deterministically grounded in a single, authoritative JSON record "
        "(<code>data/profile.json</code>), strictly validated against a comprehensive JSON Schema (<code>data/profile.schema.json</code>). "
        "The system enforces a <b>strict zero-hallucination guarantee</b>: the assistant never assumes, extrapolates, or fabricates facts "
        "that are absent from the record.",
        body_style
    ))

    story.append(Paragraph("<b>Record Structure Breakdown:</b>", h2_style))
    story.append(Paragraph(
        "• <b>Personal Information:</b> Full name (Amirreza Dorosti), Student ID (403110466), role, institution, email, GitHub profile.<br/>"
        "• <b>Courses:</b> CE4051 (AI-Native Systems Design), CE4042 (Compiler Design), CE4033 (Distributed Operating Systems).<br/>"
        "• <b>Projects:</b> MiniLang Optimizing Compiler (Rust/LLVM), RaftKV Distributed Store (Go/Raft), Neural Semantic Code Search (PyTorch/FAISS).<br/>"
        "• <b>Limits & Guardrails:</b> Clear authority boundaries (cannot book appointments, send emails, or make contractual commitments) and prohibited topics.<br/>"
        "• <b>Career & Literature Catalog:</b> Targeted engineering roles and curated textbook recommendations linked directly to completed courses and projects.",
        body_style
    ))

    story.append(Paragraph("<b>Visitor Visibility Matrix (Field-Level Permissions):</b>", h2_style))
    story.append(Paragraph(
        "The table below explicitly marks which fields a visitor is permitted to see versus fields that are strictly shielded.",
        body_style
    ))

    vis_data = [
        [Paragraph("<b>Category</b>", body_style), Paragraph("<b>Fields & Path in Schema</b>", body_style), Paragraph("<b>Visibility</b>", body_style), Paragraph("<b>System Enforcement Policy</b>", body_style)],
        [Paragraph("Personal Info", body_style), Paragraph("<code>name, student_number, role, institution, email, github_username</code>", code_style), Paragraph("<font color='#16a34a'><b>Public</b></font>", body_style), Paragraph("Directly accessible and answerable to any visitor.", body_style)],
        [Paragraph("Private Phone", body_style), Paragraph("<code>personal_info.phone_number.value</code>", code_style), Paragraph("<font color='#dc2626'><b>Restricted</b></font>", body_style), Paragraph("Strictly shielded. Deterministic guardrail refusal before LLM invocation.", body_style)],
        [Paragraph("Courses", body_style), Paragraph("<code>courses[*].(code, title, term, topics)</code>", code_style), Paragraph("<font color='#16a34a'><b>Public</b></font>", body_style), Paragraph("Fully visible: CE4051, CE4042, CE4033.", body_style)],
        [Paragraph("Projects", body_style), Paragraph("<code>projects[*].(name, summary, tech_stack, key_features)</code>", code_style), Paragraph("<font color='#16a34a'><b>Public</b></font>", body_style), Paragraph("Fully visible. Missing facts (e.g. <code>deployment_date: null</code>) are explicitly acknowledged as unrecorded.", body_style)],
        [Paragraph("Limits & Boundaries", body_style), Paragraph("<code>guardrails_and_limits.(authority_boundaries, behavioral_rules)</code>", code_style), Paragraph("<font color='#16a34a'><b>Public</b></font>", body_style), Paragraph("Transparently communicated so visitors understand what the assistant can and cannot do.", body_style)],
        [Paragraph("Reading & Job Fit", body_style), Paragraph("<code>reading_recommendations_catalog, job_fit_profile</code>", code_style), Paragraph("<font color='#16a34a'><b>Public</b></font>", body_style), Paragraph("Career preferences, target engineering roles, and course-linked textbook recommendations.", body_style)]
    ]
    vis_table = Table(vis_data, colWidths=[75, 160, 65, 204])
    vis_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(vis_table)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3: SECTION 3 (Three Production Traces from Live App)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3. Production Traces from the Live Page", h1_style))
    story.append(Paragraph(
        "The following three traces were generated directly on the live production deployment at <b>https://aboutdorost.darkube.ir</b>. "
        "Each log reports the visitor's question, recognized intent, fields retrieved, action/capability invoked, and final response.",
        body_style
    ))

    # TRACE 1
    t1_box = [
        [Paragraph("<b>TRACE 1: Good Answer with Missing Fact Acknowledgment</b>", ParagraphStyle('T1', parent=body_style, textColor=colors.HexColor("#1e3a8a"), fontName="Helvetica-Bold"))],
        [Paragraph("<b>Question:</b> Tell me about the MiniLang compiler project.", body_style)],
        [Paragraph("<b>Intent:</b> <code>project_summary</code>", body_style)],
        [Paragraph("<b>Fields read:</b> <code>projects[compiler].name, projects[compiler].summary, projects[compiler].tech_stack, projects[compiler].key_features, projects[compiler].deployment_date</code>", body_style)],
        [Paragraph("<b>Capability:</b> <code>answer_from_record</code>", body_style)],
        [Paragraph("<b>Answer:</b> <i>\"The MiniLang Optimizing Compiler is an optimizing compiler for a statically-typed toy language targeting x86-64 assembly. It is built using Rust, LLVM, and x86-64 Assembly. Key features include a LALR(1) parser with detailed syntax error recovery, an SSA-based intermediate representation with constant folding and dead code elimination, and a Chaitin-style graph coloring register allocator. The record does not list a deployment date, so I cannot provide that information.\"</i>", body_style)],
        [Paragraph("<b>Audit Note:</b> Faithfully describes the compiler project from record attributes and acknowledges <code>deployment_date: null</code> without fabricating a fictitious date.", callout_style)]
    ]
    t1_table = Table(t1_box, colWidths=[504])
    t1_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#86efac")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bbf7d0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether(t1_table))
    story.append(Spacer(1, 8))

    # TRACE 2
    t2_box = [
        [Paragraph("<b>TRACE 2: Privacy Refusal (Protected Contact Information)</b>", ParagraphStyle('T2', parent=body_style, textColor=colors.HexColor("#991b1b"), fontName="Helvetica-Bold"))],
        [Paragraph("<b>Question:</b> What is Amirreza Dorosti's phone number?", body_style)],
        [Paragraph("<b>Intent:</b> <code>refusal</code>", body_style)],
        [Paragraph("<b>Fields read:</b> <code>guardrails_and_limits.restricted_topics</code>", body_style)],
        [Paragraph("<b>Capability:</b> <code>refuse_fact</code>", body_style)],
        [Paragraph("<b>Answer:</b> <i>\"I'm sorry, but I'm not able to share that information. Amirreza Dorosti's phone number is strictly private and will not be shared.\"</i>", body_style)],
        [Paragraph("<b>Audit Note:</b> Intercepted by deterministic privacy guardrail. Refusal executed immediately with zero token hallucination or prompt leakage.", callout_style)]
    ]
    t2_table = Table(t2_box, colWidths=[504])
    t2_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#fca5a5")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#fecaca")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether(t2_table))
    story.append(Spacer(1, 8))

    # TRACE 3
    t3_box = [
        [Paragraph("<b>TRACE 3: Clarifying Question (Ambiguity Resolution)</b>", ParagraphStyle('T3', parent=body_style, textColor=colors.HexColor("#854d0e"), fontName="Helvetica-Bold"))],
        [Paragraph("<b>Question:</b> Tell me about your project.", body_style)],
        [Paragraph("<b>Intent:</b> <code>clarification</code>", body_style)],
        [Paragraph("<b>Fields read:</b> <code>projects[compiler].name, projects[raft_kv].name, projects[neural_search].name</code>", body_style)],
        [Paragraph("<b>Capability:</b> <code>ask_clarification</code>", body_style)],
        [Paragraph("<b>Answer:</b> <i>\"Could you clarify which project you mean? Amirreza Dorosti has three projects: MiniLang Optimizing Compiler, RaftKV Distributed Key-Value Store, and Neural Semantic Code Search Engine.\"</i>", body_style)],
        [Paragraph("<b>Audit Note:</b> Proactively disambiguates the user request by presenting the list of existing projects rather than making an arbitrary assumption.", callout_style)]
    ]
    t3_table = Table(t3_box, colWidths=[504])
    t3_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fefce8")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#fde047")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#fef08a")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether(t3_table))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4: SECTION 4 & 5 (External Tools, UI Trace Panel & Submission Checklist)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. Dynamic External Tool Calling (GitHub Integration)", h1_style))
    story.append(Paragraph(
        "To complement the static record grounding, the application features an integrated live GitHub tool "
        "(<code>backend/services/github_service.py</code>) communicating with the official GitHub REST API. "
        "When visitors ask about recent codebase activities (e.g. <i>\"What is the latest commit on the Dedit repository?\"</i>), "
        "the engine selects <code>capability: call_external_api</code>, fetches real-time commit SHAs, dates, and messages, "
        "and produces an accurate, verifiable answer grounded in real GitHub activity.",
        body_style
    ))

    story.append(Paragraph("5. Interactive Frontend & Trace Inspection", h1_style))
    story.append(Paragraph(
        "The single-page web client at <font color='#1d4ed8'><b>https://aboutdorost.darkube.ir</b></font> features:<br/>"
        "• <b>Live Chat Interface:</b> Conversational bubble UI with real-time markdown parsing and question suggestions.<br/>"
        "• <b>Expandable Explainability Panel:</b> Clicking <i>'Inspect Reasoning & Trace'</i> reveals the exact intent, capability, "
        "retrieved profile fields, and audit spans highlighted with their grounding source.<br/>"
        "• <b>Grounding Source Badges:</b> Every sentence in the answer is tagged as <code>record_grounded</code>, "
        "<code>missing_fact_notice</code>, or <code>guardrail_refusal</code>, giving visitors full transparency.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Submission Verification Checklist:</b>", h2_style))
    
    check_table_data = [
        [Paragraph("<b>Item</b>", body_style), Paragraph("<b>Requirement</b>", body_style), Paragraph("<b>Verification Status</b>", body_style)],
        [Paragraph("1. Public URL", body_style), Paragraph("Hosted on Hamravesh Darkube PaaS", body_style), Paragraph("<b>Live:</b> <font color='#1d4ed8'>https://aboutdorost.darkube.ir</font>", body_style)],
        [Paragraph("2. Git Repository", body_style), Paragraph("Public GitHub repo with full history", body_style), Paragraph("<b>Synced:</b> <font color='#1d4ed8'>https://github.com/Dorostwef/AboutMe</font>", body_style)],
        [Paragraph("3. JSON Profile & Schema", body_style), Paragraph("Courses, projects, limits, and field permissions", body_style), Paragraph("<b>Present:</b> <code>data/profile.json</code>, <code>profile.schema.json</code>", body_style)],
        [Paragraph("4. Production Traces", body_style), Paragraph("Good answer, refusal, clarifying question", body_style), Paragraph("<b>Included:</b> Section 3 with full fields & audit spans", body_style)],
        [Paragraph("5. Generic LLM Config", body_style), Paragraph("Universal <code>API_KEY</code>, <code>URL</code>, <code>MODEL</code> support", body_style), Paragraph("<b>Verified:</b> Supports OpenRouter, Cloudflare, Groq, local", body_style)],
        [Paragraph("6. Student Identity", body_style), Paragraph("Amirreza Dorosti (403110466)", body_style), Paragraph("<b>Consistent:</b> Applied across code, schemas, and UI", body_style)]
    ]
    chk_table = Table(check_table_data, colWidths=[100, 190, 214])
    chk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(chk_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF built successfully: {filename}")

if __name__ == "__main__":
    build_pdf()
