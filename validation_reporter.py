import json
import os
import datetime
from typing import Dict, List, Any, Optional
from utils.general_utils import save_json


class ValidationReporter:
    """
    Utility class to generate comprehensive validation reports.
    """
    
    def __init__(self, output_directory: str, document_type: str):
        self.output_directory = output_directory
        self.document_type = document_type
        self.report_data = {
            "document_type": document_type,
            "validation_timestamp": datetime.datetime.now().isoformat(),
            "samples_processed": 0,
            "validation_summary": {
                "total_validations": 0,
                "successful_validations": 0,
                "failed_validations": 0,
                "corrections_applied": 0
            },
            "field_analysis": {},
            "common_issues": {},
            "sample_reports": []
        }
    
    def add_sample_report(
        self, 
        sample_id: str, 
        validation_result: Dict[str, Any], 
        corrections_made: Optional[List[Dict[str, Any]]] = None
    ):
        """Add a report for a single sample validation."""
        
        sample_report = {
            "sample_id": sample_id,
            "validation_result": validation_result,
            "corrections_made": corrections_made or [],
            "validation_successful": validation_result.get("is_valid", False),
            "confidence_score": validation_result.get("confidence_score", 0.0),
            "issues_found": len(validation_result.get("issues", []))
        }
        
        self.report_data["sample_reports"].append(sample_report)
        self.report_data["samples_processed"] += 1
        
        # Update summary statistics
        self.report_data["validation_summary"]["total_validations"] += 1
        if validation_result.get("is_valid", False):
            self.report_data["validation_summary"]["successful_validations"] += 1
        else:
            self.report_data["validation_summary"]["failed_validations"] += 1
        
        if corrections_made:
            self.report_data["validation_summary"]["corrections_applied"] += len(corrections_made)
        
        # Analyze field-level issues
        for issue in validation_result.get("issues", []):
            field_name = issue.get("field_name", "unknown")
            issue_type = issue.get("issue_type", "unknown")
            
            if field_name not in self.report_data["field_analysis"]:
                self.report_data["field_analysis"][field_name] = {
                    "total_issues": 0,
                    "issue_types": {},
                    "samples_affected": []
                }
            
            self.report_data["field_analysis"][field_name]["total_issues"] += 1
            self.report_data["field_analysis"][field_name]["samples_affected"].append(sample_id)
            
            if issue_type not in self.report_data["field_analysis"][field_name]["issue_types"]:
                self.report_data["field_analysis"][field_name]["issue_types"][issue_type] = 0
            self.report_data["field_analysis"][field_name]["issue_types"][issue_type] += 1
            
            # Track common issues across all samples
            if issue_type not in self.report_data["common_issues"]:
                self.report_data["common_issues"][issue_type] = {
                    "count": 0,
                    "fields_affected": set(),
                    "description": issue.get("description", "")
                }
            
            self.report_data["common_issues"][issue_type]["count"] += 1
            self.report_data["common_issues"][issue_type]["fields_affected"].add(field_name)
    
    def generate_summary_statistics(self) -> Dict[str, Any]:
        """Generate summary statistics for the validation process."""
        
        if self.report_data["samples_processed"] == 0:
            return {"error": "No samples processed"}
        
        total_samples = self.report_data["samples_processed"]
        successful_rate = (
            self.report_data["validation_summary"]["successful_validations"] / total_samples * 100
        )
        
        # Convert sets to lists for JSON serialization
        for issue_type, issue_data in self.report_data["common_issues"].items():
            if isinstance(issue_data["fields_affected"], set):
                issue_data["fields_affected"] = list(issue_data["fields_affected"])
        
        # Find most problematic fields
        problematic_fields = sorted(
            self.report_data["field_analysis"].items(),
            key=lambda x: x[1]["total_issues"],
            reverse=True
        )[:10]  # Top 10 most problematic fields
        
        summary = {
            "success_rate": round(successful_rate, 2),
            "total_corrections_applied": self.report_data["validation_summary"]["corrections_applied"],
            "average_confidence_score": self._calculate_average_confidence(),
            "most_common_issues": sorted(
                self.report_data["common_issues"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:5],
            "most_problematic_fields": [(field, data["total_issues"]) for field, data in problematic_fields],
            "recommendations": self._generate_recommendations()
        }
        
        return summary
    
    def _calculate_average_confidence(self) -> float:
        """Calculate average confidence score across all samples."""
        if not self.report_data["sample_reports"]:
            return 0.0
        
        total_confidence = sum(
            report.get("confidence_score", 0.0) 
            for report in self.report_data["sample_reports"]
        )
        return round(total_confidence / len(self.report_data["sample_reports"]), 3)
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        success_rate = (
            self.report_data["validation_summary"]["successful_validations"] / 
            max(self.report_data["samples_processed"], 1) * 100
        )
        
        if success_rate < 70:
            recommendations.append(
                "Low success rate detected. Consider reviewing field mapping logic or form templates."
            )
        
        # Analyze common issues
        common_issues = self.report_data["common_issues"]
        if "wrong_location" in common_issues and common_issues["wrong_location"]["count"] > 3:
            recommendations.append(
                "Multiple wrong location issues detected. Review field name overlay generation."
            )
        
        if "wrong_label" in common_issues and common_issues["wrong_label"]["count"] > 3:
            recommendations.append(
                "Multiple wrong label issues detected. Consider improving human-readable label prompts."
            )
        
        # Analyze field-specific issues
        problematic_fields = [
            field for field, data in self.report_data["field_analysis"].items()
            if data["total_issues"] > 2
        ]
        
        if len(problematic_fields) > 5:
            recommendations.append(
                f"Multiple fields ({len(problematic_fields)}) showing consistent issues. "
                "Consider form-specific template adjustments."
            )
        
        if not recommendations:
            recommendations.append("Validation performance looks good. Continue monitoring.")
        
        return recommendations
    
    def save_report(self, logger=None) -> str:
        """Save the complete validation report to a JSON file."""
        
        # Generate final summary
        self.report_data["summary_statistics"] = self.generate_summary_statistics()
        self.report_data["report_generated_at"] = datetime.datetime.now().isoformat()
        
        # Save report
        report_filename = f"{self.document_type}_validation_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(self.output_directory, report_filename)
        
        # If no logger provided, create a simple one or handle without logging
        if logger is None:
            # Create a dummy logger that doesn't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.addHandler(logging.NullHandler())
        
        save_json(
            data=self.report_data,
            json_path=report_path,
            data_flag=f"Validation report for {self.document_type}",
            logger=logger
        )
        
        return report_path
    
    def print_summary(self):
        """Print a human-readable summary of the validation results."""
        
        summary = self.generate_summary_statistics()
        
        print(f"\n{'='*60}")
        print(f"VALIDATION REPORT SUMMARY - {self.document_type}")
        print(f"{'='*60}")
        print(f"Samples Processed: {self.report_data['samples_processed']}")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"Average Confidence Score: {summary['average_confidence_score']}")
        print(f"Total Corrections Applied: {summary['total_corrections_applied']}")
        
        print(f"\nMost Common Issues:")
        for issue_type, issue_data in summary['most_common_issues']:
            print(f"  - {issue_type}: {issue_data['count']} occurrences")
        
        print(f"\nMost Problematic Fields:")
        for field_name, issue_count in summary['most_problematic_fields']:
            print(f"  - {field_name}: {issue_count} issues")
        
        print(f"\nRecommendations:")
        for i, recommendation in enumerate(summary['recommendations'], 1):
            print(f"  {i}. {recommendation}")
        
        print(f"{'='*60}\n")
