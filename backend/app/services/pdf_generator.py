import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_screening_pdf(screening_data, output_pdf_path):
    """
    Generates a healthcare-grade PDF screening report for AnemiaWatch.
    """
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor("#7185D1")
    accent_color = colors.HexColor("#FF8D86")
    dark_text = colors.HexColor("#20243A")
    light_bg = colors.HexColor("#F4F6FC")
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=primary_color,
        leading=24
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        textColor=colors.gray,
        leading=14
    )
    
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=dark_text,
        leading=13
    )
    
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=colors.HexColor("#991B1B"),
        leading=11
    )
    
    story = []
    
    # Header banner
    story.append(Paragraph("ANEMIAWATCH", title_style))
    story.append(Paragraph("Your health, one scan at a time. | Non-Invasive Hemoglobin Screening Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=8, spaceAfter=12))
    
    # Patient & Meta Table
    patient_info = [
        [
            Paragraph(f"<b>Patient Name:</b> {screening_data.get('patient_name', 'Anonymous')}", body_style),
            Paragraph(f"<b>Report ID:</b> #{screening_data.get('id', 'N/A')}", body_style)
        ],
        [
            Paragraph(f"<b>Age / Sex:</b> {screening_data.get('patient_age', '25')} yrs / {screening_data.get('patient_sex', 'Female').capitalize()}", body_style),
            Paragraph(f"<b>Screening Date:</b> {screening_data.get('created_at', '2026-11-14')[:19]}", body_style)
        ],
        [
            Paragraph(f"<b>Pregnancy Status:</b> {'Yes' if screening_data.get('is_pregnant') else 'No / Non-pregnant'}", body_style),
            Paragraph(f"<b>Method:</b> {screening_data.get('screening_type', 'Conjunctiva').title()}", body_style)
        ]
    ]
    
    patient_table = Table(patient_info, colWidths=[270, 260])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 10))
    
    # Primary Result Banner
    hb = screening_data.get('estimated_hb', 12.0)
    category = screening_data.get('category', 'Normal')
    confidence = screening_data.get('confidence', 95.0)
    ref_range = screening_data.get('normal_range_text', '12.0 - 16.0 g/dL')
    
    result_matrix = [
        [
            Paragraph(f"<font size=11><b>Estimated Hemoglobin</b></font><br/><font size=22 color='#7185D1'><b>{hb:.1f} g/dL</b></font>", body_style),
            Paragraph(f"<font size=11><b>Screening Assessment</b></font><br/><font size=14 color='#FF8D86'><b>{category}</b></font><br/><font size=8>Target Range: {ref_range}</font>", body_style),
            Paragraph(f"<font size=11><b>AI Confidence</b></font><br/><font size=16 color='#20243A'><b>{confidence:.1f}%</b></font><br/><font size=8>Quality: {screening_data.get('quality_status', 'Optimal')}</font>", body_style)
        ]
    ]
    result_table = Table(result_matrix, colWidths=[180, 200, 150])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E5E9FF")),
        ('BOX', (0,0), (-1,-1), 1.0, primary_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 10))
    
    # Images Section (side by side original vs processed)
    orig_img_path = screening_data.get('original_image_path')
    proc_img_path = screening_data.get('processed_image_path')
    
    story.append(Paragraph("Visual ROI & Feature Inspection", h2_style))
    img_cells = []
    
    orig_flow = Paragraph("<i>Original image unavailable</i>", body_style)
    if orig_img_path and os.path.exists(orig_img_path):
        try:
            orig_flow = RLImage(orig_img_path, width=240, height=160)
        except Exception:
            pass
            
    proc_flow = Paragraph("<i>Processed image unavailable</i>", body_style)
    if proc_img_path and os.path.exists(proc_img_path):
        try:
            proc_flow = RLImage(proc_img_path, width=240, height=160)
        except Exception:
            pass
            
    img_table = Table([
        [Paragraph("<b>Original Capture</b>", body_style), Paragraph("<b>Detected ROI & Segmentation Overlay</b>", body_style)],
        [orig_flow, proc_flow]
    ], colWidths=[265, 265])
    img_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(img_table)
    story.append(Spacer(1, 10))
    
    # Clinical Guidance & Model Info
    story.append(Paragraph("Clinical Insights & Preventive Guidance", h2_style))
    prev_text = screening_data.get('prevention', 'Maintain iron-rich diet (spinach, legumes, meat) and vitamin C.')
    risk_text = screening_data.get('risks', 'Chronic anemia can lead to severe fatigue and cardiovascular workload.')
    advice_text = screening_data.get('advice', 'Confirm with complete blood count (CBC) test with your primary healthcare provider.')
    
    recs = [
        [Paragraph("<b>Nutritional Guidance:</b>", body_style), Paragraph(prev_text, body_style)],
        [Paragraph("<b>Identified Risks:</b>", body_style), Paragraph(risk_text, body_style)],
        [Paragraph("<b>Physician Action:</b>", body_style), Paragraph(advice_text, body_style)],
        [Paragraph("<b>Model Reference:</b>", body_style), Paragraph(f"{screening_data.get('model_version', 'v1.0')} ({screening_data.get('validation_status', 'Standard Model')})", body_style)]
    ]
    recs_table = Table(recs, colWidths=[130, 400])
    recs_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(recs_table)
    story.append(Spacer(1, 12))
    
    # Disclaimer Box
    disclaimer_text = (
        "<b>CLINICAL SCREENING DISCLAIMER:</b> AnemiaWatch is an artificial intelligence-assisted non-invasive screening tool. "
        "Estimated hemoglobin values and classification categories are intended for triage, health education, and telemedicine tracking only. "
        "This report does NOT constitute a definitive medical diagnosis. Hemoglobin levels MUST be confirmed by a certified clinical laboratory "
        "using venous Complete Blood Count (CBC) or approved point-of-care photometer prior to therapeutic intervention."
    )
    disclaimer_table = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[530])
    disclaimer_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FEF2F2")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#FCA5A5")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(disclaimer_table)
    story.append(Spacer(1, 15))
    
    # Doctor Sign-Off
    doc_sign = [
        [
            Paragraph("<b>Reviewed by Attending Clinician:</b> ___________________________", body_style),
            Paragraph("<b>Signature / Date:</b> ___________________________", body_style)
        ]
    ]
    doc_table = Table(doc_sign, colWidths=[310, 220])
    story.append(doc_table)
    
    doc.build(story)
    return output_pdf_path
