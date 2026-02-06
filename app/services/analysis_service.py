import pandas as pd
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import json
from typing import Dict, List, Any
import plotly.graph_objects as go
import plotly.express as px
from app.services.minio_service import minio_service

class AnalysisService:
    @staticmethod
    def _jsonable(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: AnalysisService._jsonable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [AnalysisService._jsonable(v) for v in obj]
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return obj

    @staticmethod
    def analyze_dataset(file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Comprehensive dataset analysis with stats and insights."""
        if file_type == "text/csv":
            df = pd.read_csv(BytesIO(file_content))
        elif "excel" in file_type:
            df = pd.read_excel(BytesIO(file_content))
        else:
            raise ValueError("Unsupported format")
        
        # Basic statistics
        summary = {
            "rows": len(df),
            "columns": len(df.columns),
            "missing_values": df.isnull().sum().sum(),
            "duplicate_rows": df.duplicated().sum(),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024**2
        }
        
        # Numeric columns analysis
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            summary["numeric_stats"] = {
                col: {
                    "mean": float(df[col].mean()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "skewness": float(stats.skew(df[col].dropna()))
                } for col in numeric_cols
            }
        
        # Categorical analysis
        cat_cols = df.select_dtypes(include=['object']).columns
        if len(cat_cols) > 0:
            summary["categorical_stats"] = {
                col: {k: int(v) for k, v in df[col].value_counts().head(5).to_dict().items()}
                for col in cat_cols
            }
        
        # Correlations
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            summary["top_correlations"] = [
                {"feature1": idx, "feature2": col, "correlation": float(corr_matrix.loc[idx, col])}
                for idx in corr_matrix.columns 
                for col in corr_matrix.columns 
                if idx != col and abs(corr_matrix.loc[idx, col]) > 0.5
            ][:5]
        
        # Generate insights
        insights = AnalysisService._generate_insights(df, summary)
        summary["insights"] = insights
        
        sample_data = df.head(5).where(pd.notnull(df), None).to_dict()
        result = {
            "summary": summary,
            "columns": df.columns.tolist(),
            "sample_data": sample_data,
        }
        return AnalysisService._jsonable(result)
    
    @staticmethod
    def _generate_insights(df: pd.DataFrame, summary: Dict) -> List[str]:
        insights = []
        if summary["missing_values"] > 0:
            insights.append(f"Dataset has {summary['missing_values']} missing values")
        if summary["duplicate_rows"] > 0:
            insights.append(f"Found {summary['duplicate_rows']} duplicate rows")
        if summary.get("numeric_stats"):
            for col, stats in summary["numeric_stats"].items():
                if stats["skewness"] > 1:
                    insights.append(f"{col} is right-skewed (may need log transformation)")
        return insights
    
    @staticmethod
    def generate_charts(df: pd.DataFrame, output_dir: str) -> List[str]:
        """Generate multiple chart types and save to MinIO."""
        charts = []
        
        # Histogram for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            plt.figure(figsize=(10, 6))
            for i, col in enumerate(numeric_cols[:4]):
                plt.subplot(2, 2, i+1)
                plt.hist(df[col].dropna(), bins=30, alpha=0.7)
                plt.title(col)
            plt.tight_layout()
            chart_bytes = BytesIO()
            plt.savefig(chart_bytes, format='png', dpi=150, bbox_inches='tight')
            plt.close()
            chart_bytes.seek(0)
            
            object_name = minio_service.upload_file(
                filename="analysis_histogram.png",
                file_content=chart_bytes.read(),
                metadata={'type': 'analysis_chart'}
            )
            charts.append(minio_service.get_presigned_url(object_name))
        
        # Correlation heatmap
        if len(numeric_cols) > 1:
            plt.figure(figsize=(10, 8))
            sns.heatmap(df[numeric_cols].corr(), annot=True, cmap='coolwarm', center=0)
            plt.title("Correlation Heatmap")
            chart_bytes = BytesIO()
            plt.savefig(chart_bytes, format='png', dpi=150, bbox_inches='tight')
            plt.close()
            chart_bytes.seek(0)
            
            object_name = minio_service.upload_file(
                filename="analysis_correlation.png",
                file_content=chart_bytes.read(),
                metadata={'type': 'analysis_chart'}
            )
            charts.append(minio_service.get_presigned_url(object_name))
        
        return charts

analysis_service = AnalysisService()
