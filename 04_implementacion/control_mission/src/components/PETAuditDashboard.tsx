"use client";

import React, { useState, useEffect, useCallback } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { AlertCircle, CheckCircle, Clock, Filter, RefreshCw } from "lucide-react";

interface PETBundle {
  bundle_id: string;
  package_id: string;
  source_system: string;
  status: "validated" | "ingested" | "rejected";
  claims_count: number;
  fragments_count: number;
  created_at: string;
}

interface PETAuditDashboardProps {
  apiBaseUrl?: string;
}

const COLORS = {
  validated: "#22c55e",
  ingested: "#3b82f6",
  rejected: "#ef4444",
};

const STATUS_LABELS = {
  validated: "Validado",
  ingested: "Ingestado",
  rejected: "Rechazado",
};

export function PETAuditDashboard({ apiBaseUrl = process.env.NEXT_PUBLIC_PET_API_BASE_URL || "http://localhost:8001" }: PETAuditDashboardProps) {
  const [bundles, setBundles] = useState<PETBundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterSystem, setFilterSystem] = useState("");
  const [filterStatus, setFilterStatus] = useState<"" | "validated" | "ingested" | "rejected">("");
  const [selectedBundle, setSelectedBundle] = useState<PETBundle | null>(null);

  const fetchBundles = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (filterSystem) params.append("source_system", filterSystem);
      if (filterStatus) params.append("status", filterStatus);
      params.append("limit", "100");

      const response = await fetch(`${apiBaseUrl}/api/v1/pet/list?${params}`);
      if (!response.ok) throw new Error(`API error: ${response.statusText}`);

      const data = await response.json();
      setBundles(data.bundles || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, filterSystem, filterStatus]);

  useEffect(() => {
    fetchBundles();
  }, [fetchBundles]);

  // Estadísticas
  const totalBundles = bundles.length;
  const validatedCount = bundles.filter((b) => b.status === "validated").length;
  const rejectedCount = bundles.filter((b) => b.status === "rejected").length;
  const totalClaims = bundles.reduce((sum, b) => sum + b.claims_count, 0);
  const totalFragments = bundles.reduce((sum, b) => sum + b.fragments_count, 0);

  // Datos para gráficos
  const statusData = [
    { name: STATUS_LABELS.validated, value: bundles.filter((b) => b.status === "validated").length },
    { name: STATUS_LABELS.ingested, value: bundles.filter((b) => b.status === "ingested").length },
    { name: STATUS_LABELS.rejected, value: bundles.filter((b) => b.status === "rejected").length },
  ].filter((d) => d.value > 0);

  const systemsData = Object.entries(
    bundles.reduce(
      (acc, b) => {
        if (!acc[b.source_system]) acc[b.source_system] = 0;
        acc[b.source_system]++;
        return acc;
      },
      {} as Record<string, number>
    )
  ).map(([system, count]) => ({
    name: system,
    count,
  }));

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "validated":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "rejected":
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-blue-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    return COLORS[status as keyof typeof COLORS] || "#6b7280";
  };

  return (
    <div className="w-full bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">OpenClaw PET Auditoría</h1>
          <p className="text-gray-600">Monitoreo de bundles de evidencia académica ingestados</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-600">Total Bundles</p>
            <p className="text-3xl font-bold text-gray-900">{totalBundles}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-600">Validados</p>
            <p className="text-3xl font-bold text-green-600">{validatedCount}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-600">Rechazados</p>
            <p className="text-3xl font-bold text-red-600">{rejectedCount}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-600">Total Claims</p>
            <p className="text-3xl font-bold text-blue-600">{totalClaims}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-600">Fragmentos</p>
            <p className="text-3xl font-bold text-purple-600">{totalFragments}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="w-5 h-5 text-gray-600" />
            <h2 className="text-lg font-semibold text-gray-900">Filtros</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Sistema Origen</label>
              <input
                type="text"
                placeholder="ej. ResearchLLM-v2"
                value={filterSystem}
                onChange={(e) => setFilterSystem(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Estado</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Todos</option>
                <option value="validated">Validado</option>
                <option value="ingested">Ingestado</option>
                <option value="rejected">Rechazado</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={fetchBundles}
                disabled={loading}
                className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                {loading ? "Cargando..." : "Actualizar"}
              </button>
            </div>
          </div>
        </div>

        {/* Charts */}
        {statusData.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
            {/* Status Distribution */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Distribución por Estado</h2>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={statusData} cx="50%" cy="50%" labelLine={false} label={({ name, value }) => `${name}: ${value}`} outerRadius={80} fill="#8884d8" dataKey="value">
                    {statusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={getStatusColor(entry.name.toLowerCase())} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Systems Distribution */}
            {systemsData.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Bundles por Sistema</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={systemsData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8 flex gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">Error</p>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Bundles Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">PET Bundles Ingestados</h2>
          </div>
          {loading ? (
            <div className="px-6 py-12 text-center text-gray-500">Cargando bundles...</div>
          ) : bundles.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-500">No hay bundles con los filtros aplicados</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Bundle ID</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Paquete</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Sistema</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Estado</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Claims</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Fragmentos</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Creado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {bundles.map((bundle) => (
                    <tr key={bundle.bundle_id} onClick={() => setSelectedBundle(bundle)} className="hover:bg-gray-50 cursor-pointer">
                      <td className="px-6 py-4 text-sm text-gray-900 font-mono">{bundle.bundle_id}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{bundle.package_id}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{bundle.source_system}</td>
                      <td className="px-6 py-4 text-sm">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(bundle.status)}
                          <span className="font-medium">{STATUS_LABELS[bundle.status]}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 font-semibold">{bundle.claims_count}</td>
                      <td className="px-6 py-4 text-sm text-gray-900 font-semibold">{bundle.fragments_count}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{new Date(bundle.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Bundle Details Modal */}
        {selectedBundle && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full max-h-96 overflow-y-auto">
              <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h3 className="text-lg font-semibold text-gray-900">Detalles del Bundle</h3>
                <button onClick={() => setSelectedBundle(null)} className="text-gray-500 hover:text-gray-700">
                  ✕
                </button>
              </div>
              <div className="px-6 py-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Bundle ID</p>
                    <p className="text-sm font-mono font-semibold text-gray-900">{selectedBundle.bundle_id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Package ID</p>
                    <p className="text-sm font-mono font-semibold text-gray-900">{selectedBundle.package_id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Sistema Origen</p>
                    <p className="text-sm font-semibold text-gray-900">{selectedBundle.source_system}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Estado</p>
                    <p className="text-sm font-semibold">
                      <span className="inline-flex items-center gap-2">
                        {getStatusIcon(selectedBundle.status)} {STATUS_LABELS[selectedBundle.status]}
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Claims Auditados</p>
                    <p className="text-sm font-semibold text-gray-900">{selectedBundle.claims_count}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Fragmentos</p>
                    <p className="text-sm font-semibold text-gray-900">{selectedBundle.fragments_count}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Creado</p>
                    <p className="text-sm font-semibold text-gray-900">{new Date(selectedBundle.created_at).toLocaleString()}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default PETAuditDashboard;
