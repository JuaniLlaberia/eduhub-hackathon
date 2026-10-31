// Short names for the contract types. Every API shape comes from the generated schema.d.ts
// (`npm run contract:sync`); never hand-write one here.
import type { components } from "./schema";

type Schemas = components["schemas"];

export type AccountKPIs = Schemas["AccountKPIs"];
export type AccountProfile = Schemas["AccountProfile"];
export type AnalysisJob = Schemas["AnalysisJob"];
export type AnalysisReport = Schemas["AnalysisReport"];
export type AnalysisRequest = Schemas["AnalysisRequest"];
export type AnalyzedPost = Schemas["AnalyzedPost"];
export type ApiError = Schemas["ApiError"];
export type Draft = Schemas["Draft"];
export type DraftRequest = Schemas["DraftRequest"];
export type ErrorResponse = Schemas["ErrorResponse"];
export type FeatureFlags = Schemas["FeatureFlags"];
export type Insight = Schemas["Insight"];
export type PostRates = Schemas["PostRates"];
export type PublishRequest = Schemas["PublishRequest"];
export type PublishResult = Schemas["PublishResult"];
export type Recommendation = Schemas["Recommendation"];
export type SegmentStat = Schemas["SegmentStat"];
export type SimulationRequest = Schemas["SimulationRequest"];
export type SimulationResult = Schemas["SimulationResult"];
export type TimeSlotStat = Schemas["TimeSlotStat"];
export type Trend = Schemas["Trend"];

export type JobStatus = AnalysisJob["status"];
export type MediaType = Schemas["PostFeatures"]["media_type"];
export type LengthBucket = Schemas["PostFeatures"]["length_bucket"];
export type PostKind = Schemas["Post"]["kind"];
export type SegmentDimension = SegmentStat["dimension"];
export type InsightCategory = Insight["category"];
export type Impact = Insight["impact"];
export type PublishStatus = PublishResult["status"];
