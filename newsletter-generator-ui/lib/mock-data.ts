import type { Newsletter } from "@/app/page"

export const MOCK_NEWSLETTERS: Newsletter[] = [
  {
    id: "1",
    title: "Digital Infra Weekly — Feb 2, 2026",
    date: "2026-02-02",
    timeWindow: { start: "2026-01-26", end: "2026-02-02" },
    voiceProfile: "conversational",
    verticals: ["Data Centers", "Connectivity & Fibre", "Towers & Wireless"],
    regions: ["UK", "EU"],
    sections: {
      dataCenters: {
        bigPicture:
          "The data centre market continues to experience unprecedented growth as hyperscalers expand their footprint across key markets. Major developments in Northern Virginia and European hubs signal sustained demand for digital infrastructure capacity, with AI workloads becoming the primary driver of new capacity additions.",
        bullets: [
          {
            text: "A major hyperscaler announced plans for a 120 MW data centre in Northern Virginia, expected to be operational by Q3 2027. The project will feature state-of-the-art liquid cooling and is part of a broader push into AI training infrastructure.",
            evidenceId: "DC-001",
          },
          {
            text: "European colocation provider secured €500M in financing to expand Frankfurt and Amsterdam campuses, adding 60 MW combined capacity targeting enterprise AI deployments.",
            evidenceId: "DC-002",
          },
          {
            text: "Singapore lifted its data centre moratorium for green facilities, opening opportunities for sustainable builds in the region with strict PUE requirements below 1.3.",
            evidenceId: "DC-003",
          },
          {
            text: "UK government approved planning for three new hyperscale facilities in the Midlands corridor, totaling 200 MW and creating an estimated 2,400 jobs.",
            evidenceId: "DC-004",
          },
        ],
        evidence: [
          { id: "DC-001", title: "Hyperscaler Virginia Expansion", source: "Data Center Dynamics", url: "#" },
          { id: "DC-002", title: "European Colo Financing Round", source: "Capacity Media", url: "#" },
          { id: "DC-003", title: "Singapore Moratorium Update", source: "BroadGroup", url: "#" },
          { id: "DC-004", title: "UK Midlands Approval", source: "Data Center Dynamics", url: "#" },
        ],
      },
      connectivity: {
        bigPicture:
          "Fibre network investments remain robust as operators race to expand coverage and increase backhaul capacity to support growing data centre clusters and 5G deployments. Subsea cable projects continue to attract significant capital as demand for intercontinental bandwidth accelerates.",
        bullets: [
          {
            text: "Pan-European fibre operator announced €2B investment to connect 50 new data centres to its backbone network by 2028, prioritising low-latency routes between major financial centres.",
            evidenceId: "CF-001",
          },
          {
            text: "Subsea cable project linking EMEA to APAC regions reached financial close, expected to add 200Tbps capacity when operational in 2028.",
            evidenceId: "CF-002",
          },
          {
            text: "Rural broadband initiative in Northern Europe achieved 95% coverage milestone ahead of schedule, connecting 2.3 million previously underserved premises.",
            evidenceId: "CF-003",
          },
        ],
        evidence: [
          { id: "CF-001", title: "Pan-European Fibre Investment", source: "Telecom TV", url: "#" },
          { id: "CF-002", title: "EMEA-APAC Subsea Project", source: "Submarine Telecoms Forum", url: "#" },
          { id: "CF-003", title: "Nordic Broadband Milestone", source: "Broadband World News", url: "#" },
        ],
      },
      towers: {
        bigPicture:
          "Tower and wireless infrastructure continues its consolidation trend while operators invest heavily in 5G densification and edge compute capabilities at tower sites. The push for network sharing and infrastructure efficiency is reshaping the competitive landscape.",
        bullets: [
          {
            text: "Global tower company acquired regional operator with 5,000 sites across Central Europe for $3.2B, creating the region's largest independent infrastructure provider.",
            evidenceId: "TW-001",
          },
          {
            text: "5G densification program announced for major UK urban centres, adding 2,000 small cells over 18 months to address capacity constraints in high-traffic areas.",
            evidenceId: "TW-002",
          },
          {
            text: "Tower operators piloting edge compute installations at 500 sites to support autonomous vehicle networks and industrial IoT applications.",
            evidenceId: "TW-003",
          },
        ],
        evidence: [
          { id: "TW-001", title: "Central Europe Tower Acquisition", source: "Tower Exchange", url: "#" },
          { id: "TW-002", title: "UK 5G Densification Plans", source: "Mobile World Live", url: "#" },
          { id: "TW-003", title: "Edge Compute Tower Pilot", source: "Edge Computing World", url: "#" },
        ],
      },
    },
  },
  {
    id: "2",
    title: "Digital Infra Weekly — Jan 26, 2026",
    date: "2026-01-26",
    timeWindow: { start: "2026-01-19", end: "2026-01-26" },
    voiceProfile: "analytical",
    verticals: ["Data Centers", "Connectivity & Fibre"],
    regions: ["US", "EU"],
    sections: {
      dataCenters: {
        bigPicture:
          "North American data centre markets are seeing renewed activity as power availability improves in key metros. European operators are increasingly focused on sustainability credentials to meet tightening regulatory requirements.",
        bullets: [
          {
            text: "Phoenix emerged as the fastest-growing data centre market in North America, with over 500 MW under construction and strong power availability from renewable sources.",
            evidenceId: "DC-010",
          },
          {
            text: "Major European operator achieved carbon neutrality across its entire portfolio, setting a new benchmark for the industry.",
            evidenceId: "DC-011",
          },
        ],
        evidence: [
          { id: "DC-010", title: "Phoenix Market Analysis", source: "CBRE Research", url: "#" },
          { id: "DC-011", title: "Carbon Neutral Achievement", source: "Data Center Dynamics", url: "#" },
        ],
      },
      connectivity: {
        bigPicture:
          "Long-haul fibre investments are accelerating as operators prepare for next-generation bandwidth demands. Metro networks are being upgraded to support emerging use cases requiring ultra-low latency.",
        bullets: [
          {
            text: "Transcontinental fibre route between New York and London completed upgrade to 800G wavelengths, reducing latency by 15%.",
            evidenceId: "CF-010",
          },
          {
            text: "Major metro fibre operator announced dark fibre expansion in 12 US cities to support AI workload interconnection.",
            evidenceId: "CF-011",
          },
        ],
        evidence: [
          { id: "CF-010", title: "Transatlantic Upgrade", source: "Capacity Media", url: "#" },
          { id: "CF-011", title: "US Metro Expansion", source: "Fierce Telecom", url: "#" },
        ],
      },
      towers: {
        bigPicture: "",
        bullets: [],
        evidence: [],
      },
    },
  },
  {
    id: "3",
    title: "Digital Infra Weekly — Jan 19, 2026",
    date: "2026-01-19",
    timeWindow: { start: "2026-01-12", end: "2026-01-19" },
    voiceProfile: "formal",
    verticals: ["Data Centers", "Towers & Wireless"],
    regions: ["UK", "APAC"],
    sections: {
      dataCenters: {
        bigPicture:
          "APAC data centre markets are experiencing a surge in hyperscale demand, with particular focus on Japan and India. The UK market continues to attract significant investment despite planning challenges.",
        bullets: [
          {
            text: "Japanese data centre capacity is projected to double by 2028 as hyperscalers accelerate regional expansion plans.",
            evidenceId: "DC-020",
          },
          {
            text: "India's data centre sector attracted $2.5B in foreign investment during Q4 2025, a record quarter for the market.",
            evidenceId: "DC-021",
          },
        ],
        evidence: [
          { id: "DC-020", title: "Japan Market Outlook", source: "Structure Research", url: "#" },
          { id: "DC-021", title: "India Investment Record", source: "Economic Times", url: "#" },
        ],
      },
      connectivity: {
        bigPicture: "",
        bullets: [],
        evidence: [],
      },
      towers: {
        bigPicture:
          "Network sharing arrangements are becoming increasingly sophisticated as operators seek to reduce capital intensity while accelerating coverage expansion.",
        bullets: [
          {
            text: "Two major UK mobile operators announced expanded network sharing agreement covering 15,000 rural sites.",
            evidenceId: "TW-020",
          },
          {
            text: "APAC tower developer raised $1.8B to fund expansion across Southeast Asia, targeting 10,000 new sites by 2027.",
            evidenceId: "TW-021",
          },
        ],
        evidence: [
          { id: "TW-020", title: "UK Network Sharing Deal", source: "Mobile World Live", url: "#" },
          { id: "TW-021", title: "APAC Tower Expansion", source: "Tower Exchange", url: "#" },
        ],
      },
    },
  },
]

export function getNewsletterById(id: string): Newsletter | undefined {
  return MOCK_NEWSLETTERS.find((n) => n.id === id)
}
