import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime


def generate_invoice_pdf(invoice_no: str, customer_name: str, items: list, 
                     subtotal: float, tax_rate: float, tax_amount: float, 
                     total: float, due_date: str, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=30)
    story.append(Paragraph(f"Invoice #{invoice_no}", title))
    story.append(Spacer(1, 0.2*inch))
    
    info = f"<b>Customer:</b> {customer_name}<br/><b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}<br/><b>Due Date:</b> {due_date}"
    story.append(Paragraph(info, styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    table_data = [['Item', 'Qty', 'Unit Price', 'Amount']]
    for item in items:
        table_data.append([
            item.get('item_name', ''),
            str(item.get('quantity', 0)),
            f"${item.get('unit_price', 0):.2f}",
            f"${item.get('amount', 0):.2f}"
        ])
    
    t = Table(table_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3*inch))
    
    totals = f"<b>Subtotal:</b> ${subtotal:.2f}<br/><b>Tax ({tax_rate*100}%):</b> ${tax_amount:.2f}<br/><b>Total:</b> ${total:.2f}"
    story.append(Paragraph(totals, styles['Normal']))
    
    doc.build(story)
    return output_path