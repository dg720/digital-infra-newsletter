/**
 * API Client for Digital Infrastructure Newsletter Backend
 */

const API_BASE_URL = typeof window !== 'undefined' 
  ? (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
  : 'http://localhost:8000';

export interface TimeWindow {
  start: string;
  end: string;
}

export interface GenerateRequest {
  prompt: string;
  max_review_rounds?: number;
  active_players?: { [vertical: string]: string[] };
}

export interface GenerateResponse {
  newsletter_id: string;
  paths: {
    newsletter_md: string;
    meta: string;
  };
  status: string;
}

export interface UpdateSectionRequest {
  section_id: string;
  instruction: string;
  time_window?: TimeWindow;
}

export interface UpdateSectionResponse {
  newsletter_id: string;
  section_id: string;
  status: string;
}

export interface NewsletterMeta {
  newsletter_id: string;
  original_prompt: string;
  time_window: TimeWindow;
  voice_profile: string;
  region_focus: string | null;
  style_prompt: string | null;
  verticals_included: string[];
  created_at: string;
}

export interface EvidenceItem {
  evidence_id: string;
  title: string | null;
  source_name: string;
  url: string | null;
}

export interface Bullet {
  text: string;
  evidence_ids: string[];
  player_referenced: string | null;
}

export interface SectionData {
  section_id: string;
  big_picture: string;
  big_picture_evidence_ids: string[];
  bullets: Bullet[];
  risk_flags: string[];
}

export interface NewsletterListItem {
  id: string;
  title: string;
  date: string;
  timeWindow: TimeWindow;
  voiceProfile: string;
  verticals: string[];
  regions: string[];
}

export interface NewsletterDetail {
  id: string;
  title: string;
  date: string;
  timeWindow: TimeWindow;
  voiceProfile: string;
  verticals: string[];
  regions: string[];
  sections: {
    dataCenters: SectionForUI;
    connectivity: SectionForUI;
    towers: SectionForUI;
  };
}

export interface SectionForUI {
  bigPicture: string;
  bullets: Array<{
    text: string;
    evidenceId: string;
  }>;
  evidence: Array<{
    id: string;
    title: string;
    source: string;
    url: string;
  }>;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async generateNewsletter(request: GenerateRequest): Promise<GenerateResponse> {
    const response = await fetch(`${this.baseUrl}/newsletter/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate newsletter');
    }

    return response.json();
  }

  /**
   * Generate newsletter with SSE streaming for progress updates.
   */
  async generateNewsletterStreaming(
    request: GenerateRequest,
    onStatus?: (step: string, message: string, status: 'start' | 'complete') => void,
  ): Promise<GenerateResponse> {
    const response = await fetch(`${this.baseUrl}/newsletter/generate/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error('Failed to start generation');
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Streaming not supported');
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let result: GenerateResponse | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          const eventType = line.slice(7);
          continue;
        }
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          
          if (data.step && data.message && onStatus) {
            onStatus(data.step, data.message, data.status || 'start');
          }
          
          if (data.newsletter_id) {
            result = {
              newsletter_id: data.newsletter_id,
              paths: data.paths,
              status: data.status || 'completed',
            };
          }
          
          if (data.message && !data.step) {
            throw new Error(data.message);
          }
        }
      }
    }

    if (!result) {
      throw new Error('No response received from stream');
    }

    return result;
  }

  async updateSection(
    newsletterId: string,
    request: UpdateSectionRequest
  ): Promise<UpdateSectionResponse> {
    const response = await fetch(
      `${this.baseUrl}/newsletter/${newsletterId}/update-section`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update section');
    }

    return response.json();
  }

  async getNewsletterMarkdown(newsletterId: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/newsletter/${newsletterId}`);

    if (!response.ok) {
      throw new Error('Newsletter not found');
    }

    return response.text();
  }

  async getSectionMarkdown(newsletterId: string, sectionId: string): Promise<string> {
    const response = await fetch(
      `${this.baseUrl}/newsletter/${newsletterId}/sections/${sectionId}`
    );

    if (!response.ok) {
      throw new Error('Section not found');
    }

    return response.text();
  }

  async getArtifact<T = unknown>(newsletterId: string, artifactPath: string): Promise<T> {
    const response = await fetch(
      `${this.baseUrl}/newsletter/${newsletterId}/artifacts/${artifactPath}`
    );

    if (!response.ok) {
      throw new Error('Artifact not found');
    }

    return response.json();
  }

  async listNewsletters(): Promise<{ newsletters: string[]; count: number }> {
    const response = await fetch(`${this.baseUrl}/newsletters`);

    if (!response.ok) {
      throw new Error('Failed to list newsletters');
    }

    return response.json();
  }

  async getNewsletterMeta(newsletterId: string): Promise<NewsletterMeta> {
    return this.getArtifact<NewsletterMeta>(newsletterId, 'meta.json');
  }

  async getSectionData(newsletterId: string, sectionId: string): Promise<SectionData> {
    return this.getArtifact<SectionData>(newsletterId, `sections/${sectionId}.json`);
  }

  async getEvidencePack(newsletterId: string, sectionId: string): Promise<{ items: EvidenceItem[] }> {
    return this.getArtifact<{ items: EvidenceItem[] }>(
      newsletterId,
      `evidence/${sectionId}_pack.json`
    );
  }

  async deleteNewsletter(newsletterId: string): Promise<{ status: string; newsletter_id: string }> {
    const response = await fetch(`${this.baseUrl}/newsletter/${newsletterId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete newsletter');
    }

    return response.json();
  }
}

// Singleton instance
export const apiClient = new ApiClient();

// Helper to convert backend format to UI format
export function convertToUIFormat(
  meta: NewsletterMeta,
  sections: Record<string, SectionData>,
  evidencePacks: Record<string, { items: EvidenceItem[] }>
): NewsletterDetail {
  const verticalMap: Record<string, string> = {
    data_centers: 'Data Centers',
    connectivity_fibre: 'Connectivity & Fibre',
    towers_wireless: 'Towers & Wireless',
  };

  const uiSectionMap: Record<string, keyof NewsletterDetail['sections']> = {
    data_centers: 'dataCenters',
    connectivity_fibre: 'connectivity',
    towers_wireless: 'towers',
  };

  const convertSection = (sectionId: string): SectionForUI => {
    const section = sections[sectionId];
    const evidencePack = evidencePacks[sectionId];

    if (!section) {
      return { bigPicture: '', bullets: [], evidence: [] };
    }

    // Collect all referenced evidence IDs in order of appearance
    const allReferencedIds: string[] = [...(section.big_picture_evidence_ids || [])];
    for (const b of section.bullets) {
      allReferencedIds.push(...(b.evidence_ids || []));
    }
    // Remove duplicates while preserving order
    const uniqueIds = [...new Set(allReferencedIds)];
    const idToNum: Record<string, number> = {};
    uniqueIds.forEach((id, idx) => {
      idToNum[id] = idx + 1;
    });

    // Helper to strip evidence ID patterns like (ev_xxx) from text
    const stripEvidenceIds = (text: string): string => {
      return text
        .replace(/\s*\(ev_[a-f0-9]+\)/gi, '')  // Remove (ev_xxx) patterns
        .replace(/\s*ev_[a-f0-9]+/gi, '')      // Remove standalone ev_xxx
        .trim();
    };

    // Build big picture with citations appended
    const cleanBigPicture = stripEvidenceIds(section.big_picture);
    const bpCiteNums = (section.big_picture_evidence_ids || [])
      .slice(0, 3)
      .map(id => idToNum[id])
      .filter(Boolean);
    const bigPictureWithCites = cleanBigPicture + 
      (bpCiteNums.length > 0 ? ' ' + bpCiteNums.map(n => `[${n}]`).join('') : '');

    // Build bullets with citations appended to text
    const bulletsWithCites = section.bullets.map((b) => {
      const cleanText = stripEvidenceIds(b.text);
      const citeNums = (b.evidence_ids || [])
        .slice(0, 2)
        .map(id => idToNum[id])
        .filter(Boolean);
      const textWithCite = cleanText + 
        (citeNums.length > 0 ? ' ' + citeNums.map(n => `[${n}]`).join('') : '');
      return {
        text: textWithCite,
        evidenceId: b.evidence_ids[0] || '',
      };
    });

    // Only include evidence items that are actually referenced
    const referencedEvidence = (evidencePack?.items || [])
      .filter(e => uniqueIds.includes(e.evidence_id))
      .sort((a, b) => (idToNum[a.evidence_id] || 999) - (idToNum[b.evidence_id] || 999))
      .map((e) => ({
        id: e.evidence_id,
        title: e.title || 'Source',
        source: e.source_name,
        url: e.url || '#',
      }));

    return {
      bigPicture: bigPictureWithCites,
      bullets: bulletsWithCites,
      evidence: referencedEvidence,
    };
  };

  // Parse date from newsletter_id (format: newsletter_YYYYMMDD_xxxxxx)
  const datePart = meta.newsletter_id.split('_')[1] || '';
  const year = datePart.substring(0, 4);
  const month = datePart.substring(4, 6);
  const day = datePart.substring(6, 8);
  const formattedDate = `${year}-${month}-${day}`;

  return {
    id: meta.newsletter_id,
    title: `Digital Infra Weekly — ${new Date(formattedDate).toLocaleDateString('en-GB', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })}`,
    date: formattedDate,
    timeWindow: meta.time_window,
    voiceProfile: meta.voice_profile,
    verticals: meta.verticals_included.map((v) => verticalMap[v] || v),
    regions: meta.region_focus ? [meta.region_focus] : ['Global'],
    sections: {
      dataCenters: convertSection('data_centers'),
      connectivity: convertSection('connectivity_fibre'),
      towers: convertSection('towers_wireless'),
    },
  };
}

// Helper to fetch complete newsletter data
export async function fetchNewsletterDetail(
  newsletterId: string
): Promise<NewsletterDetail> {
  const meta = await apiClient.getNewsletterMeta(newsletterId);

  const sections: Record<string, SectionData> = {};
  const evidencePacks: Record<string, { items: EvidenceItem[] }> = {};

  for (const vertical of meta.verticals_included) {
    try {
      sections[vertical] = await apiClient.getSectionData(newsletterId, vertical);
      evidencePacks[vertical] = await apiClient.getEvidencePack(newsletterId, vertical);
    } catch {
      // Section may not exist
      sections[vertical] = {
        section_id: vertical,
        big_picture: '',
        big_picture_evidence_ids: [],
        bullets: [],
        risk_flags: [],
      };
      evidencePacks[vertical] = { items: [] };
    }
  }

  return convertToUIFormat(meta, sections, evidencePacks);
}

// Helper to fetch newsletter list
export async function fetchNewsletterList(): Promise<NewsletterListItem[]> {
  const { newsletters } = await apiClient.listNewsletters();

  const items: NewsletterListItem[] = [];

  for (const id of newsletters) {
    try {
      const meta = await apiClient.getNewsletterMeta(id);
      
      const verticalMap: Record<string, string> = {
        data_centers: 'Data Centers',
        connectivity_fibre: 'Connectivity & Fibre',
        towers_wireless: 'Towers & Wireless',
      };

      // Parse date from newsletter_id
      const datePart = id.split('_')[1] || '';
      const year = datePart.substring(0, 4);
      const month = datePart.substring(4, 6);
      const day = datePart.substring(6, 8);
      const formattedDate = `${year}-${month}-${day}`;

      items.push({
        id,
        title: `Digital Infra Weekly — ${new Date(formattedDate).toLocaleDateString('en-GB', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })}`,
        date: formattedDate,
        timeWindow: meta.time_window,
        voiceProfile: meta.voice_profile,
        verticals: meta.verticals_included.map((v) => verticalMap[v] || v),
        regions: meta.region_focus ? [meta.region_focus] : ['Global'],
      });
    } catch {
      // Skip newsletters that can't be loaded
    }
  }

  return items.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}
