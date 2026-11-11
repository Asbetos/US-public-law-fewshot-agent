/** @type {import('next').NextConfig} */
const nextConfig = {
  // No caching config needed: app/route.ts sets `dynamic = "force-dynamic"` and
  // returns `cache-control: no-store`, so every request re-reads results/ from
  // disk. (An earlier experimental.staleTimes block was invalid and is dropped.)
  agentRules: false,   // don't scatter generated agent files into this repo
};
export default nextConfig;
