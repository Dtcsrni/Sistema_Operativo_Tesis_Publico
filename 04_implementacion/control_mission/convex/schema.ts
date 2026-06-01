import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  agents: defineTable({
    name: v.string(),
    status: v.union(v.literal("idle"), v.literal("busy"), v.literal("offline")),
    nodeType: v.union(v.literal("PC"), v.literal("Edge")),
    lastSeen: v.number(), // Timestamp
    metrics: v.object({
      cpu: v.number(),
      ram: v.number(),
      npu: v.optional(v.number()),
    }),
  }).index("by_status", ["status"]),

  tasks: defineTable({
    agentId: v.optional(v.id("agents")),
    title: v.string(),
    status: v.union(v.literal("pending"), v.literal("running"), v.literal("completed"), v.literal("failed")),
    progress: v.number(),
    logs: v.array(v.string()),
    startedAt: v.optional(v.number()),
    completedAt: v.optional(v.number()),
  }).index("by_status", ["status"]),

  telemetry: defineTable({
    node: v.string(),
    metric: v.string(),
    value: v.number(),
    timestamp: v.number(),
  }).index("by_timestamp", ["timestamp"]),
});
