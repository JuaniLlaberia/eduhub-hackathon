import { Pending, SectionCard } from "@/components/section-card";
import type { AnalyzedPost } from "@/lib/api/types";

// TODO: top 3 and bottom 3 posts by score (skip score === null), each with text, formatDateTime,
// formatScore, key rates, explanation (es-AR) and a link to post.url.
export function PostHighlights({ posts }: { posts: AnalyzedPost[] }) {
  return (
    <SectionCard title="Tus posts que más y menos rindieron" description={`${posts.length} posts`}>
      <Pending />
    </SectionCard>
  );
}
