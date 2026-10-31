// Spanish (es-AR) labels for the English enum codes of the contract. Behavior: labels.test.ts.
import type {
  Impact,
  InsightCategory,
  JobStatus,
  LengthBucket,
  MediaType,
  PostKind,
  PublishStatus,
  SegmentDimension,
} from "@/lib/api/types";
import { notImplemented } from "@/lib/todo";

/** `null` means a text-only post. */
export const mediaTypeLabel: (value: MediaType) => string = notImplemented;
export const lengthBucketLabel: (value: LengthBucket) => string = notImplemented;
export const postKindLabel: (value: PostKind) => string = notImplemented;
export const segmentDimensionLabel: (value: SegmentDimension) => string = notImplemented;
export const insightCategoryLabel: (value: InsightCategory) => string = notImplemented;
export const impactLabel: (value: Impact) => string = notImplemented;
export const jobStatusLabel: (value: JobStatus) => string = notImplemented;
export const publishStatusLabel: (value: PublishStatus) => string = notImplemented;

/** Value of a SegmentStat: enum codes are translated, free-text AI labels are capitalized. */
export const segmentValueLabel: (dimension: SegmentDimension, value: string) => string = notImplemented;

/** 0 = Monday … 6 = Sunday, like the contract. */
export const weekdayLabel: (weekday: number, options?: { short?: boolean }) => string = notImplemented;
