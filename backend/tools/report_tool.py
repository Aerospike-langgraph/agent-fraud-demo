"""
Report Tool - Generates investigation reports using Mistral/Ollama.

This tool is called by the GenerateReport node to:
- Generate professional fraud investigation reports
- Use LLM to synthesize findings into readable format
- Support both Ollama (local) and Mistral API
"""

import os
import logging
import httpx
from typing import Dict, Any, List

logger = logging.getLogger("agentic_fraud.tools.report")


class ReportTool:
    """Tool for generating investigation reports using LLM."""
    
    name = "generate_report"
    description = """
    Generate a professional fraud investigation report using Mistral/Ollama.
    Synthesizes evidence, fraud ring details, and recommendations into
    a structured markdown report.
    """
    
    def __init__(
        self,
        ollama_base_url: str = None,
        ollama_model: str = None
    ):
        self.ollama_base_url = ollama_base_url or os.environ.get(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.ollama_model = ollama_model or os.environ.get(
            "OLLAMA_MODEL", "mistral"
        )
        logger.info(
            f"ReportTool initialized with Ollama: {self.ollama_base_url}, "
            f"model: {self.ollama_model}"
        )
    
    def invoke(
        self,
        case_id: str,
        suspect_account_id: str,
        fraud_ring_nodes: List[str],
        innocent_nodes: List[str],
        evidence_summary: Dict[str, Any],
        scores: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate investigation report.
        
        Args:
            case_id: Investigation case ID
            suspect_account_id: Main suspect account
            fraud_ring_nodes: Accounts in the fraud ring
            innocent_nodes: Accounts determined innocent
            evidence_summary: Evidence from EvidenceTool
            scores: Risk scores by account
            
        Returns:
            {
                "report_markdown": str
                "success": bool
                "generation_method": str
            }
        """
        logger.info(f"ReportTool.invoke: generating report for case {case_id}")
        
        # Prepare context for LLM
        context = self._prepare_context(
            case_id,
            suspect_account_id,
            fraud_ring_nodes,
            innocent_nodes,
            evidence_summary,
            scores
        )
        
        # Generate report with LLM
        try:
            report = self._generate_with_ollama(context)
            return {
                "report_markdown": report,
                "success": True,
                "generation_method": f"ollama/{self.ollama_model}"
            }
        except Exception as e:
            logger.error(f"Error generating report with Ollama: {e}")
            # Fallback to template-based report
            report = self._generate_template_report(
                case_id,
                suspect_account_id,
                fraud_ring_nodes,
                innocent_nodes,
                evidence_summary,
                scores
            )
            return {
                "report_markdown": report,
                "success": True,
                "generation_method": "template_fallback"
            }
    
    def _prepare_context(
        self,
        case_id: str,
        suspect_account_id: str,
        fraud_ring_nodes: List[str],
        innocent_nodes: List[str],
        evidence_summary: Dict[str, Any],
        scores: Dict[str, Dict[str, Any]]
    ) -> str:
        """Prepare context string for LLM prompt."""
        lines = []
        
        # Case info
        lines.append(f"CASE ID: {case_id}")
        lines.append(f"SUSPECT ACCOUNT: {suspect_account_id}")
        lines.append("")
        
        # Fraud ring
        lines.append(f"FRAUD RING ({len(fraud_ring_nodes)} accounts):")
        for acc_id in fraud_ring_nodes[:10]:
            score_info = scores.get(acc_id, {})
            lines.append(
                f"  - {acc_id}: score={score_info.get('score', 0):.2f}, "
                f"bucket={score_info.get('bucket', 'unknown')}"
            )
        if len(fraud_ring_nodes) > 10:
            lines.append(f"  ... and {len(fraud_ring_nodes) - 10} more")
        lines.append("")
        
        # Evidence summary
        summary = evidence_summary.get("summary", {})
        lines.append("EVIDENCE SUMMARY:")
        lines.append(f"  Ring size: {summary.get('ring_size', 0)}")
        lines.append(f"  Shared devices: {summary.get('shared_device_count', 0)}")
        lines.append(f"  Shared IPs: {summary.get('shared_ip_count', 0)}")
        lines.append(f"  Ring density: {summary.get('ring_density', 0):.2%}")
        lines.append(f"  Average ring score: {summary.get('avg_ring_score', 0):.2f}")
        lines.append("")
        
        # Proof bullets
        proof_bullets = evidence_summary.get("proof_bullets", [])
        if proof_bullets:
            lines.append("KEY FINDINGS:")
            for bullet in proof_bullets:
                lines.append(f"  • {bullet}")
        lines.append("")
        
        # Innocent accounts
        lines.append(f"INNOCENT ACCOUNTS ({len(innocent_nodes)}):")
        for acc_id in innocent_nodes[:5]:
            score_info = scores.get(acc_id, {})
            lines.append(
                f"  - {acc_id}: score={score_info.get('score', 0):.2f} (low risk)"
            )
        lines.append("")
        
        return "\n".join(lines)
    
    def _generate_with_ollama(self, context: str) -> str:
        """Generate report using Ollama."""
        prompt = f"""You are a fraud investigation analyst. Generate a professional investigation report based on the following data.

{context}

Generate a structured markdown report with:

1. **Executive Summary** - Brief overview and key findings
2. **Suspect Analysis** - Details on the main suspect account
3. **Fraud Ring Identification** - Members, connections, evidence
4. **Evidence Summary** - Shared infrastructure, transaction patterns
5. **Innocent Accounts** - Why they were excluded
6. **Recommendations** - Actions to take

Write in a clear, professional tone. Use markdown formatting."""

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": self.ollama_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert fraud investigation analyst."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 3000
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            report = result.get("message", {}).get("content", "")
            
            if not report:
                raise Exception("Empty response from Ollama")
            
            logger.info(f"Generated report with Ollama ({len(report)} chars)")
            return report
    
    def _generate_template_report(
        self,
        case_id: str,
        suspect_account_id: str,
        fraud_ring_nodes: List[str],
        innocent_nodes: List[str],
        evidence_summary: Dict[str, Any],
        scores: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate report using template (fallback)."""
        summary = evidence_summary.get("summary", {})
        proof_bullets = evidence_summary.get("proof_bullets", [])
        
        report = f"""# Fraud Investigation Report

## Case: {case_id}

---

## Executive Summary

This investigation analyzed account **{suspect_account_id}** and its network connections. 
A fraud ring of **{len(fraud_ring_nodes)}** accounts was identified, while **{len(innocent_nodes)}** 
connected accounts were determined to be legitimate.

---

## Fraud Ring Members

| Account ID | Risk Score | Classification |
|------------|------------|----------------|
"""
        
        for acc_id in fraud_ring_nodes[:15]:
            score_info = scores.get(acc_id, {})
            report += f"| {acc_id} | {score_info.get('score', 0):.2f} | {score_info.get('bucket', 'high')} |\n"
        
        if len(fraud_ring_nodes) > 15:
            report += f"\n*... and {len(fraud_ring_nodes) - 15} additional accounts*\n"
        
        report += f"""
---

## Evidence Summary

- **Shared Devices**: {summary.get('shared_device_count', 0)} device(s) used by multiple ring members
- **Shared IPs**: {summary.get('shared_ip_count', 0)} IP address(es) shared within the ring
- **Ring Density**: {summary.get('ring_density', 0):.1%} internal connection rate
- **Average Ring Score**: {summary.get('avg_ring_score', 0):.2f}

### Key Findings

"""
        for bullet in proof_bullets:
            report += f"- {bullet}\n"
        
        report += f"""
---

## Innocent Accounts

The following accounts were connected but determined to be legitimate:

| Account ID | Risk Score | Reason |
|------------|------------|--------|
"""
        
        for acc_id in innocent_nodes[:5]:
            score_info = scores.get(acc_id, {})
            report += f"| {acc_id} | {score_info.get('score', 0):.2f} | Low risk indicators |\n"
        
        report += f"""
---

## Recommendations

1. **Immediate Action**: Suspend or flag all {len(fraud_ring_nodes)} fraud ring accounts
2. **Investigation**: Review transaction history for the ring aggregator accounts
3. **Monitoring**: Add shared devices and IPs to watchlist
4. **No Action Required**: {len(innocent_nodes)} innocent accounts require no action

---

*Report generated automatically by Agentic Fraud Investigation System*
"""
        
        return report


def create_report_tool(
    ollama_base_url: str = None,
    ollama_model: str = None
) -> ReportTool:
    """Factory function to create ReportTool instance."""
    return ReportTool(ollama_base_url, ollama_model)
