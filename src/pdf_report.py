"""
PDF Clinical Report Generator for Eye Movement Assessment.
Generates professional PDF reports suitable for clinical documentation.
"""

import io
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


@dataclass
class ClinicInfo:
    """Clinic/practice information for report branding."""
    name: str = "Eye Movement Assessment Center"
    address: str = ""
    phone: str = ""
    email: str = ""
    logo_path: Optional[str] = None


@dataclass
class PatientInfo:
    """Patient information for reports."""
    name: str = "Anonymous"
    patient_id: str = ""
    date_of_birth: str = ""
    gender: str = ""
    notes: str = ""


class PDFReportGenerator:
    """Generates PDF clinical reports."""
    
    def __init__(self, clinic_info: Optional[ClinicInfo] = None):
        """
        Initialize report generator.
        
        Args:
            clinic_info: Optional clinic branding information
        """
        self.clinic = clinic_info or ClinicInfo()
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        """Set up custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50')
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor('#34495e')
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#7f8c8d')
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='Interpretation',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20,
            textColor=colors.HexColor('#2c3e50')
        ))
        
        self.styles.add(ParagraphStyle(
            name='Disclaimer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#95a5a6'),
            alignment=TA_CENTER
        ))
    
    def generate_pursuit_report(
        self,
        result,
        patient: Optional[PatientInfo] = None,
        output_path: Optional[str] = None,
        include_trajectory: bool = True
    ) -> str:
        """
        Generate PDF report for smooth pursuit test.
        
        Args:
            result: TestResult from smooth pursuit test
            patient: Optional patient information
            output_path: Output file path (auto-generated if None)
            include_trajectory: Whether to include trajectory plot
            
        Returns:
            Path to generated PDF file
        """
        if output_path is None:
            output_dir = Path("results")
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"report_pursuit_{timestamp}.pdf")
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # Header
        story.extend(self._build_header(patient))
        
        # Test info
        story.append(Paragraph("Smooth Pursuit Eye Movement Test", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.2*inch))
        
        test_info = [
            ["Test Date:", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Pattern:", result.pattern.value.replace("_", " ").title()],
            ["Duration:", f"{result.duration:.1f} seconds"],
            ["Frames Captured:", str(len(result.frames))]
        ]
        story.append(self._create_info_table(test_info))
        story.append(Spacer(1, 0.3*inch))
        
        # Performance Metrics
        story.append(Paragraph("Performance Metrics", self.styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
        
        metrics_data = [
            ["Metric", "Value", "Status"],
            ["Tracking Success Rate", f"{result.tracking_ratio * 100:.1f}%", 
             self._status_indicator(result.tracking_ratio * 100, 80, 60)],
            ["Accuracy Score", f"{result.accuracy_score:.1f}/100",
             self._status_indicator(result.accuracy_score, 80, 60)],
            ["Smoothness Score", f"{result.smooth_score:.1f}/100",
             self._status_indicator(result.smooth_score, 70, 50)]
        ]
        
        if result.clinical_metrics is not None:
            metrics_data.extend([
                ["Pursuit Gain", f"{result.pursuit_gain:.2f}",
                 self._status_indicator(result.pursuit_gain * 100, 80, 70)],
                ["Tracking Accuracy", f"{result.accuracy_degrees:.2f}°",
                 self._status_indicator(100 - result.accuracy_degrees * 25, 50, 25)],
                ["Catch-up Saccades", str(result.catch_up_saccade_count), ""]
            ])
        
        story.append(self._create_metrics_table(metrics_data))
        story.append(Spacer(1, 0.3*inch))
        
        # Clinical Interpretation
        story.append(Paragraph("Clinical Interpretation", self.styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
        
        interpretations = self._get_pursuit_interpretations(result)
        for interp in interpretations:
            story.append(Paragraph(f"• {interp}", self.styles['Interpretation']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Trajectory plot placeholder
        if include_trajectory:
            story.append(Paragraph("Trajectory Visualization", self.styles['SectionHeader']))
            story.append(Paragraph(
                "(Trajectory plots available in exported images)",
                self.styles['MetricLabel']
            ))
        
        # Disclaimer
        story.append(Spacer(1, 0.5*inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#bdc3c7')))
        story.append(Paragraph(
            "DISCLAIMER: This is a screening tool only. Results should be interpreted by a qualified "
            "eye care professional. This report does not constitute a medical diagnosis.",
            self.styles['Disclaimer']
        ))
        
        doc.build(story)
        return output_path
    
    def generate_saccade_report(
        self,
        result,
        patient: Optional[PatientInfo] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Generate PDF report for saccade test."""
        if output_path is None:
            output_dir = Path("results")
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"report_saccade_{timestamp}.pdf")
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # Header
        story.extend(self._build_header(patient))
        
        # Test info
        test_type = result.test_type.value.replace("_", " ").title()
        story.append(Paragraph(f"{test_type} Test Report", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.2*inch))
        
        test_info = [
            ["Test Date:", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Test Type:", test_type],
            ["Total Trials:", str(result.num_trials)],
            ["Correct Responses:", f"{result.num_correct} ({(1-result.error_rate)*100:.1f}%)"]
        ]
        story.append(self._create_info_table(test_info))
        story.append(Spacer(1, 0.3*inch))
        
        # Latency Metrics
        story.append(Paragraph("Latency Metrics", self.styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
        
        metrics_data = [["Metric", "Value", "Reference"]]
        
        if result.mean_latency_ms:
            metrics_data.append([
                "Mean Latency", f"{result.mean_latency_ms:.1f} ms", "150-250 ms (normal)"
            ])
        if result.std_latency_ms:
            metrics_data.append([
                "Latency Std Dev", f"{result.std_latency_ms:.1f} ms", ""
            ])
        
        story.append(self._create_metrics_table(metrics_data))
        story.append(Spacer(1, 0.2*inch))
        
        # Error Analysis
        story.append(Paragraph("Error Analysis", self.styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
        
        error_data = [
            ["Error Type", "Rate", "Status"],
            ["Direction Errors", f"{result.error_rate*100:.1f}%",
             self._status_indicator(100 - result.error_rate*100, 85, 70)],
            ["Anticipatory (<80ms)", f"{result.anticipatory_rate*100:.1f}%", ""],
            ["Express Saccades", f"{result.express_saccade_rate*100:.1f}%", ""]
        ]
        story.append(self._create_metrics_table(error_data))
        
        # Disclaimer
        story.append(Spacer(1, 0.5*inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#bdc3c7')))
        story.append(Paragraph(
            "DISCLAIMER: This is a screening tool only. Results should be interpreted by a qualified "
            "eye care professional. This report does not constitute a medical diagnosis.",
            self.styles['Disclaimer']
        ))
        
        doc.build(story)
        return output_path
    
    def generate_validation_report(
        self,
        result,
        patient: Optional[PatientInfo] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Generate PDF report for validation test."""
        if output_path is None:
            output_dir = Path("results")
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"report_validation_{timestamp}.pdf")
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # Header
        story.extend(self._build_header(patient))
        
        story.append(Paragraph("Gaze Accuracy Validation Report", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.2*inch))
        
        # Accuracy metrics
        story.append(Paragraph("Accuracy Metrics", self.styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
        
        acc = result.accuracy_degrees
        status = "CLINICAL GRADE" if result.meets_clinical_threshold else "NEEDS IMPROVEMENT"
        
        metrics_data = [
            ["Metric", "Value", "Threshold"],
            ["Mean Accuracy", f"{acc:.2f}°" if acc else "N/A", "<2.0°"],
            ["Precision", f"{result.precision_degrees:.2f}°" if result.precision_degrees else "N/A", ""],
            ["Points Validated", f"{result.valid_points}/{len(result.points)}", ""],
            ["Status", status, ""]
        ]
        story.append(self._create_metrics_table(metrics_data))
        
        # Disclaimer
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(
            "DISCLAIMER: This validation report confirms system accuracy at the time of testing.",
            self.styles['Disclaimer']
        ))
        
        doc.build(story)
        return output_path
    
    def _build_header(self, patient: Optional[PatientInfo]) -> List:
        """Build report header with clinic and patient info."""
        elements = []
        
        # Clinic name
        elements.append(Paragraph(self.clinic.name, self.styles['Heading1']))
        if self.clinic.address:
            elements.append(Paragraph(self.clinic.address, self.styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Patient info
        if patient:
            patient_info = [
                ["Patient Name:", patient.name],
                ["Patient ID:", patient.patient_id or "N/A"],
                ["Date of Birth:", patient.date_of_birth or "N/A"]
            ]
            elements.append(self._create_info_table(patient_info))
            elements.append(Spacer(1, 0.2*inch))
        
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#3498db')))
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_info_table(self, data: List[List[str]]) -> Table:
        """Create a simple info table."""
        table = Table(data, colWidths=[1.5*inch, 4*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#7f8c8d')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        return table
    
    def _create_metrics_table(self, data: List[List[str]]) -> Table:
        """Create a metrics table with header."""
        table = Table(data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ecf0f1')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        return table
    
    def _status_indicator(self, value: float, good_threshold: float, warn_threshold: float) -> str:
        """Return status text based on thresholds."""
        if value >= good_threshold:
            return "✓ Normal"
        elif value >= warn_threshold:
            return "~ Borderline"
        else:
            return "✗ Abnormal"
    
    def _get_pursuit_interpretations(self, result) -> List[str]:
        """Get clinical interpretations for pursuit test."""
        interpretations = []
        
        if result.clinical_metrics is not None:
            if result.pursuit_gain >= 0.8:
                interpretations.append("Pursuit gain is within normal limits (≥0.8)")
            elif result.pursuit_gain >= 0.7:
                interpretations.append("Pursuit gain is borderline (0.7-0.8) - recommend monitoring")
            else:
                interpretations.append("Pursuit gain is reduced (<0.7) - recommend further evaluation")
            
            if result.accuracy_degrees <= 2.0:
                interpretations.append("Tracking accuracy is within normal limits (≤2°)")
            else:
                interpretations.append(f"Tracking accuracy is reduced ({result.accuracy_degrees:.2f}°)")
        
        if result.smooth_score >= 70:
            interpretations.append("Eye movements are smooth with minimal saccadic intrusions")
        elif result.smooth_score >= 50:
            interpretations.append("Some saccadic intrusions noted during pursuit")
        else:
            interpretations.append("Significant saccadic intrusions - may indicate pursuit dysfunction")
        
        return interpretations
