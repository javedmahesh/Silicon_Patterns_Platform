"""The built-in ``semiconductor`` rule pack.

Pure data: the vocabularies, weights and prerequisites that define what Silicon
Patterns considers a semiconductor company, a relevant technology and a market
signal. Kept apart from :mod:`backend.market_intelligence.rules` so the *engine* and
the *business vocabulary* can change independently — tuning what the platform looks
for should never mean editing how it looks.

Every rule here can be disabled, re-weighted, re-ordered or extended by
configuration, and an overlay pack can replace any of them by key.

Two deliberate omissions:

* There is no catch-all "Other" classification. A company the vocabulary cannot
  place reports *no* classification, which is a visible, reviewable state; labelling
  it "Other" would dress an absence of evidence up as a conclusion.
* Where a fact is already reported as an engineering signal (engineering expansion,
  design services, manufacturing), the strategic layer derives an interpretation
  from it rather than emitting the same finding twice under two names.
"""
from __future__ import annotations

from typing import Callable

from backend.market_intelligence.rules import DEFAULT_THRESHOLDS, DEFAULT_WEIGHTS, Rule, RulePack
from backend.market_intelligence.schemas import RuleKind

C = RuleKind.CLASSIFICATION
T = RuleKind.TECHNOLOGY
S = RuleKind.SIGNAL

#: Fields where narrative claims live. Verb-like vocabulary ("launches", "hiring")
#: is restricted to these so a stray match in a country or headcount field cannot
#: manufacture a signal.
_NARRATIVE = ("description", "headline", "industry", "source_url", "programme")
_FUNDING_FIELDS = ("description", "headline", "funding_stage", "industry", "programme")

#: Classification keys that place a company inside the semiconductor market itself,
#: as opposed to a market that buys from it. Referenced by the startup and
#: new-entrant rules, and by the priority model's relevance factor.
CORE_CLASSIFICATIONS: tuple[str, ...] = (
    "fabless", "idm", "foundry", "eda", "ip_provider", "ai_hardware", "memory",
    "semiconductor",
)
ADJACENT_CLASSIFICATIONS: tuple[str, ...] = (
    "automotive_electronics", "robotics", "embedded_systems", "edge_computing",
    "networking", "industrial_electronics", "quantum",
)

# --------------------------------------------------------------- classification
# `priority` is specificity: the lowest-numbered match becomes the primary
# classification, so "Fabless Semiconductor" always wins over the generic
# "Semiconductor" for a company whose text supports both.
_CLASSIFICATIONS: tuple[Rule, ...] = (
    Rule(key="fabless", label="Fabless Semiconductor", kind=C, priority=10, core=True,
         terms=("fabless", "fabless semiconductor", "fabless chip company",
                "fabless model"),
         explanation="Designs silicon without owning fabrication."),
    Rule(key="idm", label="Integrated Device Manufacturer", kind=C, priority=11, core=True,
         terms=("idm", "integrated device manufacturer", "designs and manufactures its own"),
         explanation="Designs and manufactures its own devices."),
    Rule(key="foundry", label="Foundry", kind=C, priority=12, core=True,
         terms=("foundry", "pure-play foundry", "wafer foundry", "wafer fab",
                "fabrication plant", "semiconductor fab"),
         explanation="Manufactures silicon for other companies."),
    Rule(key="eda", label="EDA", kind=C, priority=13, core=True,
         terms=("eda", "electronic design automation", "design automation",
                "eda tools", "eda software"),
         explanation="Builds the tools chips are designed with."),
    Rule(key="ip_provider", label="Semiconductor IP Provider", kind=C, priority=14, core=True,
         terms=("semiconductor ip", "silicon ip", "ip core", "ip cores", "soft ip",
                "hard ip", "ip licensing", "ip portfolio", "licensable ip"),
         explanation="Licenses reusable silicon IP."),
    Rule(key="ai_hardware", label="AI Hardware", kind=C, priority=20, core=True,
         terms=("ai chip", "ai chips", "ai accelerator", "ai accelerators", "ai hardware",
                "ai silicon", "ai processor", "inference chip", "training chip", "npu",
                "neural processing unit", "tensor processing unit", "neural accelerator"),
         explanation="Builds silicon purpose-designed for AI workloads."),
    Rule(key="memory", label="Memory", kind=C, priority=21, core=True,
         terms=("dram", "nand", "sram", "hbm", "memory controller", "flash memory",
                "mram", "memory chip", "memory subsystem", "storage controller"),
         explanation="Works on memory devices or memory subsystems."),
    Rule(key="quantum", label="Quantum", kind=C, priority=22,
         terms=("quantum computing", "qubit", "qubits", "quantum processor",
                "quantum chip", "superconducting qubit"),
         explanation="Quantum computing hardware."),
    Rule(key="automotive_electronics", label="Automotive Electronics", kind=C, priority=30,
         terms=("automotive electronics", "automotive semiconductor", "automotive grade",
                "adas", "in-vehicle", "vehicle electronics", "autosar", "iso 26262",
                "automotive chip"),
         explanation="Electronics for vehicles."),
    Rule(key="robotics", label="Robotics", kind=C, priority=31,
         terms=("robotics", "robot", "robots", "robotic", "autonomous mobile robot",
                "humanoid", "cobot"),
         explanation="Robotics systems or platforms."),
    Rule(key="embedded_systems", label="Embedded Systems", kind=C, priority=32,
         terms=("embedded systems", "embedded system", "embedded software", "firmware",
                "microcontroller", "mcu", "rtos", "bare metal", "embedded design"),
         explanation="Embedded compute and firmware."),
    Rule(key="edge_computing", label="Edge Computing", kind=C, priority=33,
         terms=("edge computing", "edge ai", "edge inference", "on-device", "edge device",
                "tinyml", "at the edge"),
         explanation="Compute deployed at the edge rather than the datacentre."),
    Rule(key="networking", label="Networking", kind=C, priority=34,
         terms=("networking", "ethernet", "switch asic", "network processor",
                "optical networking", "network silicon", "5g", "rf front end"),
         explanation="Networking silicon or systems."),
    Rule(key="industrial_electronics", label="Industrial Electronics", kind=C, priority=35,
         terms=("industrial automation", "industrial electronics", "power electronics",
                "motor control", "industrial iot", "plc"),
         explanation="Electronics for industrial systems."),
    # The generic fallback. Last by priority, so it is only the *primary*
    # classification when nothing more specific matched.
    Rule(key="semiconductor", label="Semiconductor", kind=C, priority=50, core=True,
         terms=("semiconductor", "semiconductors", "microelectronics",
                "integrated circuit", "integrated circuits", "silicon chip",
                "chip design", "chipmaker", "chip maker", "chips", "wafer", "vlsi",
                "tapeout", "tape-out", "custom silicon", "asic", "soc"),
         explanation="Operates in the semiconductor market."),
)

# ------------------------------------------------------------------ technology
# The vocabulary that decides technology overlap with Silicon Patterns' services.
# A technology term is a direct statement about what a company builds, so these
# start from a higher base confidence than an inferred classification.
_TECHNOLOGIES: tuple[Rule, ...] = (
    Rule(key="asic", label="ASIC", kind=T, category="design", base_confidence=0.7,
         terms=("asic", "asics", "application specific integrated circuit")),
    Rule(key="rtl", label="RTL", kind=T, category="design", base_confidence=0.7,
         terms=("rtl", "register transfer level", "verilog", "systemverilog", "vhdl")),
    Rule(key="fpga", label="FPGA", kind=T, category="design", base_confidence=0.7,
         terms=("fpga", "fpgas", "field programmable gate array")),
    Rule(key="soc", label="SoC", kind=T, category="design", base_confidence=0.7,
         terms=("soc", "socs", "system on chip", "system-on-chip")),
    Rule(key="physical_design", label="Physical Design", kind=T, category="design",
         base_confidence=0.7,
         terms=("physical design", "place and route", "floorplanning", "synthesis",
                "signoff", "static timing analysis")),
    Rule(key="verification", label="Verification", kind=T, category="verification",
         base_confidence=0.7,
         terms=("verification", "functional verification", "uvm", "formal verification",
                "design verification")),
    Rule(key="dft", label="DFT", kind=T, category="verification", base_confidence=0.7,
         terms=("dft", "design for test", "design-for-test", "scan chain", "atpg", "mbist")),
    Rule(key="risc_v", label="RISC-V", kind=T, category="architecture", base_confidence=0.7,
         terms=("risc-v", "riscv", "risc v")),
    Rule(key="chiplet", label="Chiplet", kind=T, category="packaging", base_confidence=0.7,
         terms=("chiplet", "chiplets", "die-to-die", "ucie")),
    Rule(key="packaging", label="Packaging", kind=T, category="packaging", base_confidence=0.7,
         terms=("packaging", "substrate", "osat", "wafer level packaging", "flip chip")),
    Rule(key="advanced_packaging", label="Advanced Packaging", kind=T, category="packaging",
         base_confidence=0.7,
         terms=("advanced packaging", "cowos", "fan-out", "hybrid bonding",
                "heterogeneous integration")),
    Rule(key="packaging_2_5d", label="2.5D", kind=T, category="packaging", base_confidence=0.7,
         terms=("2.5d", "2.5 d", "interposer")),
    Rule(key="three_d_ic", label="3D IC", kind=T, category="packaging", base_confidence=0.7,
         terms=("3d ic", "3dic", "3d-ic", "3d stacking", "through silicon via", "tsv")),
    Rule(key="serdes", label="SerDes", kind=T, category="interface", base_confidence=0.7,
         terms=("serdes", "ser-des", "high speed io", "high-speed serial")),
    Rule(key="pcie", label="PCIe", kind=T, category="interface", base_confidence=0.7,
         terms=("pcie", "pci express", "pci-e", "cxl")),
    Rule(key="ddr", label="DDR", kind=T, category="memory", base_confidence=0.7,
         terms=("ddr", "ddr4", "ddr5", "lpddr", "gddr")),
    Rule(key="hbm", label="HBM", kind=T, category="memory", base_confidence=0.7,
         terms=("hbm", "hbm2", "hbm3", "high bandwidth memory")),
    Rule(key="memory_controller", label="Memory Controller", kind=T, category="memory",
         base_confidence=0.7,
         terms=("memory controller", "memory subsystem", "memory ip")),
    Rule(key="ai_accelerator", label="AI Accelerator", kind=T, category="ai",
         base_confidence=0.7,
         terms=("ai accelerator", "ai accelerators", "accelerator chip", "npu",
                "neural accelerator", "deep learning accelerator")),
    Rule(key="inference", label="Inference", kind=T, category="ai", base_confidence=0.7,
         terms=("inference", "inferencing", "model serving")),
    Rule(key="training", label="Training", kind=T, category="ai", base_confidence=0.7,
         terms=("model training", "training cluster", "training workload",
                "large language model training", "pretraining")),
    Rule(key="cuda", label="CUDA", kind=T, category="ai", base_confidence=0.7,
         terms=("cuda", "cudnn", "tensorrt")),
    Rule(key="tensor", label="Tensor", kind=T, category="ai", base_confidence=0.7,
         terms=("tensor", "tensor core", "tensor cores", "tensorflow")),
    Rule(key="compute", label="Compute", kind=T, category="compute", base_confidence=0.7,
         terms=("compute", "gpu", "gpus", "cpu", "dsp", "accelerated computing",
                "high performance computing")),
    Rule(key="networking_ip", label="Networking", kind=T, category="networking",
         base_confidence=0.7,
         terms=("network on chip", "noc", "interconnect", "switch fabric", "infiniband",
                "nvlink")),
    Rule(key="ethernet", label="Ethernet", kind=T, category="networking", base_confidence=0.7,
         terms=("ethernet", "800g", "400g", "mac phy")),
    Rule(key="automotive", label="Automotive", kind=T, category="automotive",
         base_confidence=0.7,
         terms=("automotive", "adas", "autonomous driving", "in-vehicle", "autosar")),
    Rule(key="functional_safety", label="Safety", kind=T, category="automotive",
         base_confidence=0.7,
         terms=("functional safety", "safety critical", "asil", "safety certification",
                "iec 61508")),
    Rule(key="iso_26262", label="ISO 26262", kind=T, category="automotive",
         base_confidence=0.8, terms=("iso 26262", "iso26262")),
)

# ------------------------------------------------------------ engineering signals
_ENGINEERING: tuple[Rule, ...] = (
    Rule(key="engineering_hiring", label="Engineering Hiring", kind=S,
         category="engineering", signal_type="engineering_hiring", priority=10,
         base_confidence=0.55, fields=_NARRATIVE,
         terms=("hiring", "we are hiring", "job openings", "open roles", "careers",
                "join our team", "recruiting engineers", "engineering jobs",
                "open positions"),
         explanation="The company is publicly recruiting engineers."),
    Rule(key="engineering_expansion", label="Engineering Expansion", kind=S,
         category="engineering", signal_type="engineering_expansion", priority=11,
         base_confidence=0.6, fields=_NARRATIVE,
         terms=("engineering expansion", "expanding the team", "scaling the team",
                "growing our engineering", "new design centre", "new design center",
                "doubling the team", "team expansion", "expanding operations",
                "opening a new office"),
         explanation="The company is expanding its engineering capacity."),
    Rule(key="design_services", label="Design Services", kind=S, category="engineering",
         signal_type="design_services", priority=12, base_confidence=0.65,
         terms=("design services", "turnkey design", "asic design services",
                "soc design services", "vlsi services", "design partner",
                "engineering services", "design house"),
         explanation="The company buys or sells silicon design services."),
    Rule(key="verification_services", label="Verification Services", kind=S,
         category="engineering", signal_type="verification_services", priority=13,
         base_confidence=0.65,
         terms=("verification services", "dv services", "verification ip",
                "verification team", "functional verification"),
         explanation="Verification work is being done or sourced."),
    Rule(key="silicon_ip", label="Silicon IP", kind=S, category="engineering",
         signal_type="silicon_ip", priority=14, base_confidence=0.65,
         terms=("silicon ip", "ip core", "ip cores", "ip licensing", "semiconductor ip",
                "ip block", "licensable ip"),
         explanation="The company works with licensable silicon IP."),
    Rule(key="eda_usage", label="EDA Usage", kind=S, category="engineering",
         signal_type="eda_usage", priority=15, base_confidence=0.6,
         terms=("cadence", "synopsys", "siemens eda", "mentor graphics", "eda tools",
                "innovus", "primetime", "vcs", "questa", "calibre")),
    Rule(key="chip_development", label="Chip Development", kind=S, category="engineering",
         signal_type="chip_development", priority=16, base_confidence=0.7,
         terms=("chip development", "developing a chip", "first silicon", "tapeout",
                "tape-out", "silicon bring-up", "bring-up", "custom silicon",
                "designing its own chip", "in-house silicon")),
    Rule(key="manufacturing_activity", label="Manufacturing Activity", kind=S,
         category="engineering", signal_type="manufacturing_activity", priority=17,
         base_confidence=0.6,
         terms=("fabrication", "wafer production", "assembly and test", "osat",
                "mass production", "volume production", "fab capacity",
                "manufacturing line", "production line")),
    Rule(key="product_launch", label="Product Launch", kind=S, category="engineering",
         signal_type="product_launch", priority=18, base_confidence=0.55,
         fields=_NARRATIVE,
         terms=("launch", "launches", "launched", "unveiled", "unveils",
                "general availability", "now available", "product launch")),
    Rule(key="technology_announcement", label="Technology Announcement", kind=S,
         category="engineering", signal_type="technology_announcement", priority=19,
         base_confidence=0.5, fields=_NARRATIVE,
         terms=("announced", "announces", "introduces", "introducing",
                "new architecture", "next generation", "breakthrough")),
    Rule(key="engineering_centre", label="Engineering Centre", kind=S,
         category="engineering", signal_type="engineering_centre", priority=20,
         base_confidence=0.65,
         terms=("design centre", "design center", "engineering centre",
                "engineering center", "r&d centre", "r&d center", "development centre",
                "development center", "global capability centre", "gcc")),
)

# --------------------------------------------------------------- funding signals
_FUNDING: tuple[Rule, ...] = (
    Rule(key="seed_funding", label="Seed", kind=S, category="funding",
         signal_type="seed", priority=30, base_confidence=0.65, fields=_FUNDING_FIELDS,
         terms=("seed", "seed round", "seed funding", "pre-seed", "preseed",
                "seed-stage", "angel round")),
    Rule(key="series_a", label="Series A", kind=S, category="funding",
         signal_type="series_a", priority=31, base_confidence=0.7, fields=_FUNDING_FIELDS,
         terms=("series a",)),
    Rule(key="series_b", label="Series B", kind=S, category="funding",
         signal_type="series_b", priority=32, base_confidence=0.7, fields=_FUNDING_FIELDS,
         terms=("series b",)),
    Rule(key="series_c_plus", label="Series C+", kind=S, category="funding",
         signal_type="series_c", priority=33, base_confidence=0.7, fields=_FUNDING_FIELDS,
         terms=("series c", "series d", "series e", "series f", "growth round")),
    Rule(key="ipo", label="IPO", kind=S, category="funding", signal_type="ipo",
         priority=34, base_confidence=0.75, fields=_FUNDING_FIELDS,
         terms=("ipo", "initial public offering", "public listing", "listed on nasdaq",
                "went public")),
    Rule(key="strategic_investment", label="Strategic Investment", kind=S,
         category="funding", signal_type="strategic_investment", priority=35,
         base_confidence=0.65, fields=_FUNDING_FIELDS,
         terms=("strategic investment", "strategic investor", "corporate venture",
                "strategic round", "strategic backing")),
    Rule(key="grant_funding", label="Grant", kind=S, category="funding",
         signal_type="grant", priority=36, base_confidence=0.6, fields=_FUNDING_FIELDS,
         terms=("grant", "grant funding", "awarded a grant", "research grant")),
    Rule(key="government_funding", label="Government Funding", kind=S, category="funding",
         signal_type="government_funding", priority=37, base_confidence=0.7,
         fields=_FUNDING_FIELDS,
         terms=("government funding", "government grant", "public funding",
                "state funding", "india semiconductor mission", "chips act", "meity",
                "ministry of electronics", "subsidy", "incentive scheme")),
    # Deliberately no bare "accelerator": in this corpus that word is far more often
    # an AI accelerator (a chip) than an accelerator programme, and treating hardware
    # as a funding signal would put a false Accelerator Member on real companies.
    Rule(key="accelerator", label="Accelerator", kind=S, category="funding",
         signal_type="accelerator", priority=38, base_confidence=0.6,
         fields=_FUNDING_FIELDS,
         terms=("accelerator program", "accelerator programme", "startup accelerator",
                "y combinator", "techstars", "startup program", "startup programme")),
    Rule(key="incubator", label="Incubator", kind=S, category="funding",
         signal_type="incubator", priority=39, base_confidence=0.6,
         fields=_FUNDING_FIELDS,
         terms=("incubator", "incubated", "incubation")),
)

# ------------------------------------------------------------- strategic signals
# Evaluated after classification, technology and the other signal categories, so
# these may depend on them. Most are *derived*: they carry no vocabulary of their
# own and inherit the evidence of what they depend on.
_SEMI_ANY = (CORE_CLASSIFICATIONS,)
_STARTUP_ANY = ("fact:early_stage", "fact:recently_founded", "seed_funding", "series_a",
                "accelerator", "incubator")

_STRATEGIC: tuple[Rule, ...] = (
    Rule(key="new_market_entrant", label="New Market Entrant", kind=S, category="strategic",
         signal_type="new_market_entrant", priority=60, base_confidence=0.55,
         requires=("fact:first_sighting",),
         requires_any=(CORE_CLASSIFICATIONS + ADJACENT_CLASSIFICATIONS,),
         explanation="First time the platform has seen this company in a relevant market."),
    Rule(key="semiconductor_startup", label="Semiconductor Startup", kind=S,
         category="strategic", signal_type="semiconductor_startup", priority=61,
         base_confidence=0.65,
         requires_any=(CORE_CLASSIFICATIONS, _STARTUP_ANY),
         explanation="An early-stage company inside the semiconductor market."),
    Rule(key="chip_startup", label="Chip Startup", kind=S, category="strategic",
         signal_type="chip_startup", priority=62, base_confidence=0.7,
         requires=("chip_development",), requires_any=(_STARTUP_ANY,),
         explanation="An early-stage company actively developing silicon."),
    Rule(key="ai_hardware_company", label="AI Hardware Company", kind=S, category="strategic",
         signal_type="ai_hardware_company", priority=63, base_confidence=0.7,
         requires=("ai_hardware",),
         explanation="Builds silicon for AI workloads."),
    Rule(key="eda_company", label="EDA Company", kind=S, category="strategic",
         signal_type="eda_company", priority=64, base_confidence=0.7, requires=("eda",),
         explanation="Builds electronic design automation tooling."),
    Rule(key="fabless_company", label="Fabless Company", kind=S, category="strategic",
         signal_type="fabless_company", priority=65, base_confidence=0.7,
         requires=("fabless",),
         explanation="Designs silicon without owning fabrication."),
    Rule(key="ip_company", label="IP Company", kind=S, category="strategic",
         signal_type="ip_company", priority=66, base_confidence=0.7,
         requires=("ip_provider",),
         explanation="Licenses silicon IP to other companies."),
    Rule(key="automotive_market", label="Automotive Electronics", kind=S,
         category="strategic", signal_type="automotive_electronics", priority=67,
         base_confidence=0.65, requires=("automotive_electronics",),
         explanation="Operates in vehicle electronics."),
    Rule(key="edge_ai", label="Edge AI", kind=S, category="strategic", signal_type="edge_ai",
         priority=68, base_confidence=0.65,
         terms=("edge ai", "edge inference", "on-device ai", "tinyml",
                "inference at the edge"),
         explanation="Runs AI workloads on edge silicon."),
    Rule(key="strategic_partnership", label="Strategic Partnership", kind=S,
         category="strategic", signal_type="strategic_partnership", priority=69,
         base_confidence=0.55, fields=_NARRATIVE,
         terms=("strategic partnership", "partners with", "in partnership with",
                "joint venture", "strategic alliance", "collaboration with")),
    Rule(key="technology_launch", label="Technology Launch", kind=S, category="strategic",
         signal_type="technology_launch", priority=70, base_confidence=0.6,
         requires_any=(("product_launch", "technology_announcement"),
                       CORE_CLASSIFICATIONS + ADJACENT_CLASSIFICATIONS),
         explanation="A relevant company has announced or launched technology."),
    Rule(key="accelerator_member", label="Accelerator Member", kind=S, category="strategic",
         signal_type="accelerator_member", priority=71, base_confidence=0.6,
         requires_any=(("accelerator", "incubator"),),
         explanation="Member of an accelerator or incubator programme."),
    Rule(key="government_initiative", label="Government Initiative", kind=S,
         category="strategic", signal_type="government_initiative", priority=72,
         base_confidence=0.65, requires=("government_funding",),
         explanation="Backed by a public semiconductor programme."),
    Rule(key="manufacturing_capability", label="Manufacturing Capability", kind=S,
         category="strategic", signal_type="manufacturing_capability", priority=73,
         base_confidence=0.65, requires=("manufacturing_activity",),
         explanation="Has or is building manufacturing capability."),
    Rule(key="design_services_provider", label="Design Services", kind=S,
         category="strategic", signal_type="design_services_provider", priority=74,
         base_confidence=0.65, requires=("design_services",),
         explanation="Engages in silicon design services."),
    # Ecosystem membership is business context, so it is interpreted here rather than
    # asserted by the connector that happened to surface the company.
    Rule(key="nvidia_ecosystem", label="NVIDIA Ecosystem", kind=S, category="strategic",
         signal_type="nvidia_ecosystem", priority=75, base_confidence=0.6,
         sources=("nvidia_inception",),
         explanation="Surfaced through NVIDIA's published ecosystem."),
)


def default_pack() -> RulePack:
    """The built-in ``semiconductor`` pack. A fresh object each call — packs are
    immutable, but overlays build on this and must not alias a shared instance."""
    return RulePack(
        name="semiconductor",
        version="1.0",
        rules=tuple(sorted(_CLASSIFICATIONS + _TECHNOLOGIES + _ENGINEERING + _FUNDING
                           + _STRATEGIC, key=lambda r: (r.priority, r.key))),
        thresholds=dict(DEFAULT_THRESHOLDS),
        weights=dict(DEFAULT_WEIGHTS),
    )


#: Every pack the platform ships with. An overlay may extend any of them by name.
BUILTIN_PACKS: dict[str, Callable[[], RulePack]] = {"semiconductor": default_pack}
