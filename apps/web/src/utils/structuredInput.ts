import type { StructuredInputModel } from "../types/chat";

export type StructuredInputKey =
  | "task"
  | "context"
  | "materials"
  | "urlReferences"
  | "constraints"
  | "outputPreference";

export interface StructuredInputDraft {
  task: string;
  context: string;
  materialsText: string;
  urlReferencesText: string;
  constraints: string;
  outputPreference: string;
}

export interface StructuredInputSection {
  key: StructuredInputKey;
  title: string;
  heading: string;
  value: string;
  items?: string[];
}

export interface ParsedStructuredUserTurn {
  task: string;
  context: string;
  materials: string[];
  urlReferences: string[];
  constraints: string;
  outputPreference: string;
  sections: StructuredInputSection[];
}

interface NormalizedStructuredInput {
  task: string;
  context: string;
  materials: string[];
  urlReferences: string[];
  constraints: string;
  outputPreference: string;
}

const TASK_HEADING = "【任务】";
const CONTEXT_HEADING = "【已知背景/材料】";
const MATERIALS_HEADING = "【补充材料/笔记】";
const URL_REFERENCES_HEADING = "【链接参考 / URL 引用】";
const CONSTRAINTS_HEADING = "【约束要求】";
const OUTPUT_PREFERENCE_HEADING = "【输出偏好】";
const MATERIALS_MARKER_PREFIX = "[材料 ";
const URL_REFERENCES_MARKER_PREFIX = "[链接 ";
const MARKER_SUFFIX = "]";

export const EMPTY_STRUCTURED_INPUT_DRAFT: StructuredInputDraft = {
  task: "",
  context: "",
  materialsText: "",
  urlReferencesText: "",
  constraints: "",
  outputPreference: "",
};

export const STRUCTURED_INPUT_SECTIONS: ReadonlyArray<Omit<StructuredInputSection, "items" | "value">> = [
  { key: "task", title: "任务/问题", heading: TASK_HEADING },
  { key: "context", title: "已知背景/材料", heading: CONTEXT_HEADING },
  { key: "materials", title: "补充材料/笔记", heading: MATERIALS_HEADING },
  { key: "urlReferences", title: "链接参考 / URL 引用", heading: URL_REFERENCES_HEADING },
  { key: "constraints", title: "约束要求", heading: CONSTRAINTS_HEADING },
  { key: "outputPreference", title: "输出偏好", heading: OUTPUT_PREFERENCE_HEADING },
];

function normalizeText(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value).replace(/\r\n?/g, "\n").trim();
}

function splitNonEmptyLines(value: string): string[] {
  return normalizeText(value)
    .split(/\n+/)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export function splitMaterialsText(value: string): string[] {
  return normalizeText(value)
    .split(/\n\s*\n+/)
    .map((block) => block.trim())
    .filter(Boolean);
}

export function splitUrlReferencesText(value: string): string[] {
  return splitNonEmptyLines(value);
}

export function isValidUrlReference(value: string): boolean {
  const normalized = normalizeText(value);
  return /^https?:\/\/\S+$/i.test(normalized) && !/\s/.test(normalized);
}

export function getInvalidUrlReferences(value: string): string[] {
  return splitUrlReferencesText(value).filter((entry) => !isValidUrlReference(entry));
}

function normalizeMaterials(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((entry) => normalizeText(entry))
      .filter(Boolean);
  }
  if (typeof value === "string") {
    return splitMaterialsText(value);
  }
  return [];
}

function normalizeUrlReferences(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((entry) => normalizeText(entry))
      .filter(Boolean);
  }
  if (typeof value === "string") {
    return splitUrlReferencesText(value);
  }
  return [];
}

function normalizeInput(
  draft: Partial<StructuredInputDraft> | Partial<StructuredInputModel> | ParsedStructuredUserTurn,
): NormalizedStructuredInput {
  const materialsFromDraft =
    "materialsText" in draft
      ? normalizeMaterials((draft as Partial<StructuredInputDraft>).materialsText)
      : normalizeMaterials((draft as Partial<StructuredInputModel> & { materials?: unknown }).materials);

  const urlReferencesFromDraft =
    "urlReferencesText" in draft
      ? normalizeUrlReferences((draft as Partial<StructuredInputDraft>).urlReferencesText)
      : normalizeUrlReferences(
          (draft as Partial<StructuredInputModel> & { urlReferences?: unknown }).urlReferences,
        );

  return {
    task: normalizeText(draft.task),
    context: normalizeText(draft.context),
    materials: materialsFromDraft,
    urlReferences: urlReferencesFromDraft,
    constraints: normalizeText(draft.constraints),
    outputPreference: normalizeText(draft.outputPreference),
  };
}

function composeMaterialsSection(materials: string[]): string {
  return materials.map((material, index) => `${materialMarkerLabel(index)}\n${material}`).join("\n\n");
}

function composeUrlReferencesSection(urlReferences: string[]): string {
  return urlReferences
    .map((urlReference, index) => `${urlReferenceMarkerLabel(index)}\n${urlReference}`)
    .join("\n\n");
}

function parseNumberedSectionItems(
  value: string,
  markerPrefix: string,
  validateItem: (item: string) => boolean,
): string[] | null {
  const normalized = normalizeText(value);
  if (!normalized) {
    return null;
  }

  const lines = normalized.split("\n");
  const items: string[] = [];
  let currentIndex = 0;
  let currentLines: string[] = [];

  function flushCurrentItem(): boolean {
    if (currentIndex <= 0) {
      return true;
    }
    const block = currentLines.join("\n").trim();
    if (!block || !validateItem(block)) {
      return false;
    }
    items.push(block);
    currentLines = [];
    return true;
  }

  for (const line of lines) {
    const trimmed = line.trim();
    const markerMatch = new RegExp(`^\\${markerPrefix}(\\d+)\\]$`).exec(trimmed);
    if (markerMatch) {
      const nextIndex = Number(markerMatch[1]);
      const expectedIndex = currentIndex > 0 ? currentIndex + 1 : 1;
      if (nextIndex !== expectedIndex) {
        return null;
      }
      if (!flushCurrentItem()) {
        return null;
      }
      currentIndex = nextIndex;
      continue;
    }

    if (currentIndex <= 0) {
      if (trimmed) {
        return null;
      }
      continue;
    }

    currentLines.push(line);
  }

  if (!flushCurrentItem() || !items.length) {
    return null;
  }

  return items;
}

function parseMaterialsSectionValue(value: string): string[] | null {
  return parseNumberedSectionItems(value, MATERIALS_MARKER_PREFIX, (item) => Boolean(item.trim()));
}

function parseUrlReferencesSectionValue(value: string): string[] | null {
  return parseNumberedSectionItems(value, URL_REFERENCES_MARKER_PREFIX, isValidUrlReference);
}

export function getStructuredInputValidationError(
  draft: Partial<StructuredInputDraft> | Partial<StructuredInputModel> | ParsedStructuredUserTurn,
): string | null {
  const normalized = normalizeInput(draft);
  if (!normalized.task) {
    return "任务/问题不能为空。";
  }
  if (normalized.urlReferences.some((entry) => !isValidUrlReference(entry))) {
    return "链接参考必须以 http:// 或 https:// 开头，且每行只能填写一个链接。";
  }
  return null;
}

export function toStructuredInputModel(
  draft: Partial<StructuredInputDraft> | Partial<StructuredInputModel> | ParsedStructuredUserTurn,
): StructuredInputModel | null {
  const normalized = normalizeInput(draft);
  if (getStructuredInputValidationError(normalized)) {
    return null;
  }

  return {
    task: normalized.task,
    ...(normalized.context ? { context: normalized.context } : {}),
    ...(normalized.materials.length ? { materials: normalized.materials } : {}),
    ...(normalized.urlReferences.length ? { urlReferences: normalized.urlReferences } : {}),
    ...(normalized.constraints ? { constraints: normalized.constraints } : {}),
    ...(normalized.outputPreference ? { outputPreference: normalized.outputPreference } : {}),
  };
}

export function getStructuredInputSections(
  draft: Partial<StructuredInputDraft> | Partial<StructuredInputModel> | ParsedStructuredUserTurn,
): StructuredInputSection[] {
  const normalized = normalizeInput(draft);

  return STRUCTURED_INPUT_SECTIONS.flatMap((section) => {
    if (section.key === "materials") {
      if (!normalized.materials.length) {
        return [];
      }
      return [
        {
          ...section,
          value: composeMaterialsSection(normalized.materials),
          items: normalized.materials,
        },
      ];
    }

    if (section.key === "urlReferences") {
      if (!normalized.urlReferences.length) {
        return [];
      }
      return [
        {
          ...section,
          value: composeUrlReferencesSection(normalized.urlReferences),
          items: normalized.urlReferences,
        },
      ];
    }

    const value = normalized[section.key as Exclude<StructuredInputKey, "materials" | "urlReferences">];
    return value ? [{ ...section, value }] : [];
  });
}

export function composeStructuredPrompt(
  draft: Partial<StructuredInputDraft> | Partial<StructuredInputModel> | ParsedStructuredUserTurn,
): string {
  const normalized = normalizeInput(draft);
  const hasSupplementalInput = Boolean(
    normalized.context ||
      normalized.materials.length ||
      normalized.urlReferences.length ||
      normalized.constraints ||
      normalized.outputPreference,
  );

  if (!normalized.task) {
    return "";
  }

  if (!hasSupplementalInput) {
    return normalized.task;
  }

  return getStructuredInputSections(normalized)
    .map((section) => `${section.heading}\n${section.value}`)
    .join("\n\n");
}

export function parseStructuredUserTurn(text: string): ParsedStructuredUserTurn | null {
  const normalized = normalizeText(text);
  if (!normalized.startsWith("【")) {
    return null;
  }

  const draft: ParsedStructuredUserTurn = {
    task: "",
    context: "",
    materials: [],
    urlReferences: [],
    constraints: "",
    outputPreference: "",
    sections: [],
  };

  const lines = normalized.split("\n");
  const seen = new Set<StructuredInputKey>();
  let currentSection: (typeof STRUCTURED_INPUT_SECTIONS)[number] | null = null;
  let currentLines: string[] = [];
  let lastSectionIndex = -1;

  function flushCurrentSection(): boolean {
    if (!currentSection) {
      return true;
    }
    const value = currentLines.join("\n").trim();
    if (!value) {
      return false;
    }

    if (currentSection.key === "materials") {
      const materials = parseMaterialsSectionValue(value);
      if (!materials?.length) {
        return false;
      }
      draft.materials = materials;
      draft.sections.push({
        ...currentSection,
        value,
        items: materials,
      });
      currentLines = [];
      return true;
    }

    if (currentSection.key === "urlReferences") {
      const urlReferences = parseUrlReferencesSectionValue(value);
      if (!urlReferences?.length) {
        return false;
      }
      draft.urlReferences = urlReferences;
      draft.sections.push({
        ...currentSection,
        value,
        items: urlReferences,
      });
      currentLines = [];
      return true;
    }

    draft[currentSection.key] = value;
    draft.sections.push({ ...currentSection, value });
    currentLines = [];
    return true;
  }

  for (const line of lines) {
    const headingIndex = STRUCTURED_INPUT_SECTIONS.findIndex((section) => section.heading === line.trim());

    if (headingIndex >= 0) {
      const nextSection = STRUCTURED_INPUT_SECTIONS[headingIndex];
      if (headingIndex < lastSectionIndex || seen.has(nextSection.key)) {
        return null;
      }
      if (!flushCurrentSection()) {
        return null;
      }
      currentSection = nextSection;
      seen.add(nextSection.key);
      lastSectionIndex = headingIndex;
      continue;
    }

    if (!currentSection) {
      return null;
    }

    currentLines.push(line);
  }

  if (!flushCurrentSection() || draft.sections.length === 0 || !draft.task) {
    return null;
  }

  return draft;
}

export function isStructuredUserTurn(text: string): boolean {
  return parseStructuredUserTurn(text) !== null;
}

export function materialsTextFromItems(materials: string[]): string {
  return normalizeMaterials(materials).join("\n\n");
}

export function urlReferencesTextFromItems(urlReferences: string[]): string {
  return normalizeUrlReferences(urlReferences).join("\n");
}

export function materialMarkerLabel(index: number): string {
  return `${MATERIALS_MARKER_PREFIX}${index + 1}${MARKER_SUFFIX}`;
}

export function urlReferenceMarkerLabel(index: number): string {
  return `${URL_REFERENCES_MARKER_PREFIX}${index + 1}${MARKER_SUFFIX}`;
}
