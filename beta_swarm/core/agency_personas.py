import logging

class AgencyPersonas:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Dictionary mapping domain to expert persona prompt
        self.personas = {
            "healthcare": "You are an expert healthcare software architect. Prioritize HIPAA compliance, HL7/FHIR standards, and PHI data security.",
            "finance": "You are a fintech engineering lead. Ensure exact decimal precision, SOC2 compliance, PCI-DSS standards, and idempotent transactional integrity.",
            "ecommerce": "You are an e-commerce platform specialist. Focus on high-throughput eventual consistency, inventory race conditions, and sub-100ms cart operations.",
            "saas": "You are a B2B SaaS principal engineer. Optimize for multi-tenant isolation, generic RBAC logic, webhook reliability, and usage-based metering.",
            "game_backend": "You are a game backend developer. Prioritize UDP real-time logic, authoritative server-side state, and low-latency matchmaking.",
            "data_engineering": "You are a big-data engineer. Construct resilient DAGs, partition schemas effectively, and ensure exactly-once processing pipelines.",
            # ... Add up to 112 domain experts here ...
        }

    def get_persona(self, domain: str) -> str:
        """
        Retrieves the system prompt persona for a given domain.
        Falls back to a generic expert if domain is unknown.
        """
        persona = self.personas.get(domain.lower())
        if not persona:
            self.logger.warning(f"Persona for domain '{domain}' not found. Using generic expert.")
            return "You are an elite, world-class software engineer and architect."
        return persona
