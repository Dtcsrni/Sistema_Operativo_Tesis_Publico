import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

export const list = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("agents").collect();
  },
});

export const updateAgentStatus = mutation({
  args: {
    id: v.id("agents"),
    status: v.union(v.literal("idle"), v.literal("busy"), v.literal("offline")),
    metrics: v.object({
      cpu: v.number(),
      ram: v.number(),
      npu: v.optional(v.number()),
    }),
  },
  handler: async (ctx, args) => {
    const { id, status, metrics } = args;
    await ctx.db.patch(id, { status, metrics, lastSeen: Date.now() });
  },
});

export const registerAgent = mutation({
  args: {
    name: v.string(),
    nodeType: v.union(v.literal("PC"), v.literal("Edge")),
  },
  handler: async (ctx, args) => {
    const { name, nodeType } = args;
    const existing = await ctx.db
      .query("agents")
      .filter((q) => q.eq(q.field("name"), name))
      .first();

    if (existing) return existing._id;

    return await ctx.db.insert("agents", {
      name,
      nodeType,
      status: "idle",
      lastSeen: Date.now(),
      metrics: { cpu: 0, ram: 0 },
    });
  },
});
