import math
import os
from pathlib import Path
from typing import Optional, Dict, Any
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas


class CertificateGenerator:
    """
    Renders high-resolution, vector-based PDF certificates based on a predefined
    luxury corporate/academic template using ReportLab.
    """

    @classmethod
    def generate(
        cls,
        output_path: str,
        recipient_name: str,
        event_title: str,
        issuer_name: str,
        issue_date: str,
        certificate_number: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Generates a PDF certificate at output_path.
        Returns the file size in bytes.
        """
        # Ensure parent directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        c = canvas.Canvas(output_path, pagesize=landscape(A4))
        width, height = landscape(A4)  # 841.89 x 595.27 points

        # 1. Background Fill (Subtle off-white luxury paper tone)
        c.setFillColor(colors.HexColor("#FAFBFD"))
        c.rect(0, 0, width, height, fill=1, stroke=0)

        # 2. Outer Border (Deep Midnight Navy)
        c.setStrokeColor(colors.HexColor("#0F172A"))
        c.setLineWidth(4)
        margin_outer = 26
        c.rect(margin_outer, margin_outer, width - (margin_outer * 2), height - (margin_outer * 2))

        # 3. Inner Border (Metallic Accent Gold)
        c.setStrokeColor(colors.HexColor("#D4AF37"))
        c.setLineWidth(1.5)
        margin_inner = 34
        c.rect(margin_inner, margin_inner, width - (margin_inner * 2), height - (margin_inner * 2))

        # 4. Corner Geometric Accents (Gold diamonds)
        def draw_corner(cx: float, cy: float):
            c.saveState()
            c.setFillColor(colors.HexColor("#D4AF37"))
            c.setStrokeColor(colors.HexColor("#0F172A"))
            c.setLineWidth(0.8)
            p = c.beginPath()
            d = 7
            p.moveTo(cx, cy + d)
            p.lineTo(cx + d, cy)
            p.lineTo(cx, cy - d)
            p.lineTo(cx - d, cy)
            p.close()
            c.drawPath(p, fill=1, stroke=1)
            c.restoreState()

        draw_corner(margin_inner + 4, margin_inner + 4)
        draw_corner(width - margin_inner - 4, margin_inner + 4)
        draw_corner(margin_inner + 4, height - margin_inner - 4)
        draw_corner(width - margin_inner - 4, height - margin_inner - 4)

        # 5. Top Header: Issuer Name
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(colors.HexColor("#64748B"))
        clean_issuer = (issuer_name or "ORGANIZATION").upper()
        c.drawCentredString(width / 2, height - 74, clean_issuer)

        # Decorative header rule with center diamond
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.setLineWidth(0.75)
        c.line(width / 2 - 140, height - 84, width / 2 - 15, height - 84)
        c.line(width / 2 + 15, height - 84, width / 2 + 140, height - 84)
        draw_corner(width / 2, height - 84)

        # 6. Main Certificate Title
        c.setFont("Helvetica-Bold", 28)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.drawCentredString(width / 2, height - 128, "CERTIFICATE OF ACHIEVEMENT")

        # 7. Subtitle
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawCentredString(width / 2, height - 160, "THIS CERTIFICATE IS PROUDLY PRESENTED TO")

        # 8. Recipient Name with dynamic font size for long names
        clean_name = recipient_name.strip()
        c.setFillColor(colors.HexColor("#1E3A8A"))
        if len(clean_name) > 30:
            name_font_size = 22
        elif len(clean_name) > 20:
            name_font_size = 26
        else:
            name_font_size = 32
        c.setFont("Helvetica-Bold", name_font_size)
        c.drawCentredString(width / 2, height - 208, clean_name)

        # Gold underline accent
        name_width = min(c.stringWidth(clean_name, "Helvetica-Bold", name_font_size) + 40, width - 180)
        c.setStrokeColor(colors.HexColor("#D4AF37"))
        c.setLineWidth(2)
        c.line(width / 2 - name_width / 2, height - 218, width / 2 + name_width / 2, height - 218)

        # 9. Description / Event Text
        c.setFont("Helvetica", 12)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawCentredString(width / 2, height - 250, "for successfully participating in and completing")

        # Event Title
        c.setFont("Helvetica-Bold", 17)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.drawCentredString(width / 2, height - 278, event_title)

        # Custom Description / Subtitle
        display_desc = description
        if metadata and "grade" in metadata:
            grade_str = f"with Grade: {metadata['grade']}"
            display_desc = f"{display_desc} ({grade_str})" if display_desc else grade_str

        if display_desc:
            c.setFont("Helvetica-Oblique", 10.5)
            c.setFillColor(colors.HexColor("#64748B"))
            short_desc = display_desc if len(display_desc) <= 120 else display_desc[:117] + "..."
            c.drawCentredString(width / 2, height - 304, short_desc)

        # 10. Signatures and Seal Section
        sig_y = height - 440

        # Left Signature Line
        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setLineWidth(1)
        c.line(100, sig_y, 280, sig_y)

        c.setFont("Helvetica-Oblique", 14)
        c.setFillColor(colors.HexColor("#1E293B"))
        c.drawCentredString(190, sig_y + 12, "Signature")

        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawCentredString(190, sig_y - 16, "Authorized Signatory")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawCentredString(190, sig_y - 30, clean_issuer)

        # Right Signature Line
        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setLineWidth(1)
        c.line(width - 280, sig_y, width - 100, sig_y)

        c.setFont("Helvetica-Oblique", 14)
        c.setFillColor(colors.HexColor("#1E293B"))
        c.drawCentredString(width - 190, sig_y + 12, "Signature")

        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawCentredString(width - 190, sig_y - 16, "Program Director")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawCentredString(width - 190, sig_y - 30, "Academic Committee")

        # Center Official Vector Seal (Rosette with ribbons)
        seal_x = width / 2
        seal_y = height - 425
        c.saveState()

        # Ribbon Left
        c.setFillColor(colors.HexColor("#B45309"))
        ribbon1 = c.beginPath()
        ribbon1.moveTo(seal_x - 14, seal_y - 15)
        ribbon1.lineTo(seal_x - 24, seal_y - 58)
        ribbon1.lineTo(seal_x - 14, seal_y - 50)
        ribbon1.lineTo(seal_x - 4, seal_y - 58)
        ribbon1.lineTo(seal_x - 4, seal_y - 15)
        ribbon1.close()
        c.drawPath(ribbon1, fill=1, stroke=0)

        # Ribbon Right
        ribbon2 = c.beginPath()
        ribbon2.moveTo(seal_x + 4, seal_y - 15)
        ribbon2.lineTo(seal_x + 4, seal_y - 58)
        ribbon2.lineTo(seal_x + 14, seal_y - 50)
        ribbon2.lineTo(seal_x + 24, seal_y - 58)
        ribbon2.lineTo(seal_x + 14, seal_y - 15)
        ribbon2.close()
        c.drawPath(ribbon2, fill=1, stroke=0)

        # 24-point Star Rosette
        c.setFillColor(colors.HexColor("#D97706"))
        num_points = 24
        outer_r = 34
        inner_r = 29
        star_path = c.beginPath()
        for i in range(num_points * 2):
            r = outer_r if i % 2 == 0 else inner_r
            angle = i * math.pi / num_points
            px = seal_x + r * math.cos(angle)
            py = seal_y + r * math.sin(angle)
            if i == 0:
                star_path.moveTo(px, py)
            else:
                star_path.lineTo(px, py)
        star_path.close()
        c.drawPath(star_path, fill=1, stroke=0)

        # Outer gold disc
        c.setFillColor(colors.HexColor("#F59E0B"))
        c.circle(seal_x, seal_y, 27, fill=1, stroke=0)

        # Inner white ring
        c.setStrokeColor(colors.HexColor("#FFFFFF"))
        c.setLineWidth(1)
        c.circle(seal_x, seal_y, 23, fill=0, stroke=1)

        # Seal Stars & Verified Text
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.drawCentredString(seal_x, seal_y + 4, "★ ★ ★")
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(seal_x, seal_y - 7, "VERIFIED")
        c.restoreState()

        # 11. Footer Metadata & Verification
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(margin_inner + 18, margin_inner + 14, f"CERTIFICATE ID: {certificate_number}")
        c.drawRightString(width - margin_inner - 18, margin_inner + 14, f"DATE OF ISSUANCE: {issue_date}")

        # Watermark/Engine note
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.drawCentredString(width / 2, margin_inner + 14, "Official Verified Document • Bulk Certificate Generator Engine")

        c.save()
        return os.path.getsize(output_path)
