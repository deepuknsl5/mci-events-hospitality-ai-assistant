from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle
)

OUTPUT = "architecture/MCI_Architecture_Explanation.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    rightMargin=17 * mm,
    leftMargin=17 * mm,
    topMargin=15 * mm,
    bottomMargin=15 * mm
)

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name="MainTitle",
    parent=styles["Title"],
    fontSize=19,
    leading=23,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#17365D"),
    spaceAfter=5
))

styles.add(ParagraphStyle(
    name="Subtitle",
    parent=styles["Normal"],
    fontSize=9,
    leading=13,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#555555"),
    spaceAfter=14
))

styles.add(ParagraphStyle(
    name="Section",
    parent=styles["Heading2"],
    fontSize=11,
    leading=14,
    textColor=colors.HexColor("#17365D"),
    spaceBefore=8,
    spaceAfter=4
))

styles.add(ParagraphStyle(
    name="BodyCustom",
    parent=styles["BodyText"],
    fontSize=8.5,
    leading=12,
    spaceAfter=5
))

styles.add(ParagraphStyle(
    name="SmallCustom",
    parent=styles["BodyText"],
    fontSize=7.8,
    leading=10,
    spaceAfter=3
))

story = []

def heading(text):
    story.append(Paragraph(text, styles["Section"]))

def para(text):
    story.append(Paragraph(text, styles["BodyCustom"]))

def bullet(text):
    story.append(Paragraph("&#8226;&nbsp; " + text, styles["BodyCustom"]))

def footer(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(17 * mm, 9 * mm, "MCI Events & Hospitality AI Assistant")
    canvas.drawRightString(
        A4[0] - 17 * mm, 9 * mm,
        f"Page {document.page}"
    )
    canvas.restoreState()

# PAGE 1
story.append(Paragraph(
    "MCI Events &amp; Hospitality AI Assistant",
    styles["MainTitle"]
))
story.append(Paragraph(
    "Solution Architecture and Technical Design",
    styles["Subtitle"]
))

heading("1. Solution Overview")
para(
    "The solution is a Python-based AI assistant designed to answer attendee "
    "questions about event information, support booking-related requests, "
    "and identify conversations that require human assistance. "
    "FastAPI exposes the application through REST endpoints. The system "
    "uses event-specific knowledge retrieval to ensure that information "
    "from one event is not used to answer questions about another event."
)

heading("2. High-Level Architecture")
para(
    "The application is organized into focused components: an API layer, "
    "event and session validation, a hybrid retrieval layer, an optional "
    "local language model, booking and escalation services, and conversation "
    "logging. Event knowledge is loaded through an ingestion pipeline and "
    "indexed for both semantic and lexical retrieval."
)

heading("3. Hybrid Retrieval-Augmented Generation")
para(
    "The retrieval layer combines two complementary approaches:"
)
bullet(
    "<b>Vector search:</b> Sentence Transformers generates embeddings for "
    "event knowledge. ChromaDB stores the embeddings and associated metadata. "
    "Queries are filtered using the selected event_id."
)
bullet(
    "<b>Lexical search:</b> BM25 provides keyword-based retrieval. "
    "Separate BM25 indexes are built dynamically for each event using "
    "the event_id metadata."
)
bullet(
    "<b>Rank fusion:</b> Reciprocal Rank Fusion (RRF) combines the vector "
    "and BM25 rankings. Common stopwords are removed during lexical "
    "tokenization to reduce irrelevant matches."
)
bullet(
    "<b>Relevance filtering:</b> Candidates are evaluated using the "
    "configured vector similarity threshold and positive lexical matches. "
    "Relevant retrieved content is used to construct the answer context."
)
para(
    "This hybrid approach supports both semantic questions and exact "
    "keyword-based questions. When relevant context is unavailable, "
    "the application uses a safe extractive fallback instead of inventing "
    "event-specific information."
)

heading("4. Answer Generation")
para(
    "A local Ollama model, configured as Qwen 2.5 1.5B, can optionally "
    "generate answers using retrieved event context. The model is disabled "
    "by default to keep the prototype lightweight. When the model is disabled "
    "or unavailable, the application can use its extractive response path. "
    "The LLM is not treated as the source of event facts; retrieved knowledge "
    "provides the grounding context."
)

heading("5. Request and Data Flow")
para(
    "An attendee sends a request with event and session context. The API "
    "validates the event context and routes the request to the appropriate "
    "service. Booking requests use the mock booking service. Knowledge "
    "questions use the event-filtered hybrid retriever. VIP or dissatisfied "
    "attendees can trigger escalation handling. The response is assembled "
    "and returned to the attendee, while conversation turns are recorded "
    "in JSONL logs."
)

story.append(PageBreak())

# PAGE 2
story.append(Paragraph(
    "Security, Reliability and Operations",
    styles["MainTitle"]
))

heading("6. Event Isolation and Security")
para(
    "Event isolation is enforced at retrieval time. ChromaDB vector queries "
    "apply an event_id metadata filter, while BM25 retrieval uses the "
    "corresponding event-specific index. This prevents a query for one event "
    "from retrieving knowledge belonging to another event."
)
para(
    "The application validates event context and includes protection "
    "against cross-event requests. Retrieved event content is used as "
    "reference data rather than as trusted instructions. Prompt-injection "
    "attempts should not be allowed to override system rules, event scope, "
    "or application-level validation. Production deployment should add "
    "strong authentication, authorization, input validation, rate limiting, "
    "and secret management."
)

heading("7. Booking and Human Escalation")
para(
    "Booking-related requests are handled through a dedicated mock booking "
    "API service. Keeping booking operations separate from knowledge "
    "retrieval makes it easier to replace the mock service with a real "
    "booking provider integration."
)
para(
    "The escalation service identifies VIP or dissatisfied attendee "
    "conversations that require human attention. Escalation is handled "
    "separately from ordinary knowledge responses so that sensitive "
    "or unhappy customer interactions can be routed for assistance."
)

heading("8. Conversation Logging and Monitoring")
para(
    "Conversation turns are recorded in JSONL format. Structured logs "
    "support debugging, conversation review, and analysis of application "
    "behavior. In production, monitoring should include request latency, "
    "retrieval quality, fallback frequency, booking errors, escalation "
    "volume, model errors, and API availability. Logs should avoid storing "
    "unnecessary personal or sensitive information."
)

heading("9. Scalability and Deployment")
para(
    "For a production workload of approximately 200,000 daily users, "
    "the application can be deployed as stateless FastAPI instances behind "
    "a load balancer. Session state and booking data should be stored in "
    "shared, scalable services rather than local process memory. "
    "The retrieval layer can be scaled independently, with persistent "
    "vector storage, event-aware indexing, caching for frequently requested "
    "information, and asynchronous processing for suitable background tasks."
)
para(
    "A production Azure deployment could use Azure Container Apps or "
    "Azure Kubernetes Service for application hosting, managed identity "
    "and Key Vault for secrets, and Azure Monitor or Application Insights "
    "for observability. These are deployment options, not components "
    "required by the current local prototype."
)

heading("10. Cost Optimization")
bullet(
    "Use the lightweight embedding model and retrieve only a limited "
    "number of relevant candidates."
)
bullet(
    "Keep the local Ollama model optional and disabled by default."
)
bullet(
    "Use extractive fallback responses when an LLM call is unnecessary "
    "or unavailable."
)
bullet(
    "Cache frequently requested event information where appropriate."
)
bullet(
    "Separate booking, retrieval, and generation services so each can "
    "be scaled according to its workload."
)

heading("11. Current Prototype Limitations")
para(
    "The current implementation uses local ChromaDB storage, a mock booking "
    "service, JSONL conversation logs, and an optional local LLM. It is a "
    "working prototype rather than a fully production-hardened platform. "
    "Production readiness would require real booking integration, durable "
    "shared session storage, authentication and authorization, operational "
    "monitoring, load testing, and deployment-level security controls."
)

heading("12. Technology Stack")
data = [
    ["Layer", "Technology"],
    ["API", "Python, FastAPI"],
    ["Embeddings", "Sentence Transformers"],
    ["Vector retrieval", "ChromaDB"],
    ["Lexical retrieval", "BM25 / rank-bm25"],
    ["Ranking", "Reciprocal Rank Fusion"],
    ["Optional generation", "Ollama / Qwen 2.5 1.5B"],
    ["Logging", "JSONL conversation logs"],
    ["Testing", "Pytest"]
]

table = Table(data, colWidths=[48 * mm, 125 * mm])
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 0), (-1, -1), 7.8),
    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCCCCC")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
     [colors.white, colors.HexColor("#F2F5F9")]),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))

story.append(Spacer(1, 3))
story.append(table)

doc.build(story, onFirstPage=footer, onLaterPages=footer)

print(f"Architecture explanation generated: {OUTPUT}")
