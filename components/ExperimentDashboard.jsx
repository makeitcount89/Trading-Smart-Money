// components/ExperimentDashboard.jsx
import React, { useEffect, useState } from 'react';

export default function ExperimentDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/experiment_results.json')
      .then(res => res.json())
      .then(json => {
        setData(json);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error loading experiment results:", err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-6 text-center text-gray-400">Parsing multi-year universe data...</div>;
  if (!data) return <div className="p-6 text-center text-red-400">Failed to load execution logs.</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="border-b border-gray-800 pb-4">
        <h2 className="text-xl font-bold text-white">Macro Universe Experiment</h2>
        <p className="text-sm text-gray-400">Comparing structural order block entry mechanics across ETFs, Equities, and Short Funds.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* GROUP 1: PURE PROXIMITY */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-start">
              <h3 className="text-lg font-semibold text-gray-200">{data.group1.name}</h3>
              <span className="px-2 py-0.5 text-xs font-mono rounded bg-amber-950 text-amber-400 border border-amber-800">
                Unfiltered
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">Routes $50 weekly to the asset absolute closest to weekly structural support.</p>
            
            <div className="mt-6 space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Total Invested:</span>
                <span className="text-sm font-mono text-gray-200">${data.group1.invested.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Ending Portfolio Value:</span>
                <span className="text-sm font-mono text-gray-200">${Math.round(data.group1.value).toLocaleString()}</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-gray-800 flex justify-between items-baseline">
            <span className="text-sm text-gray-400">Strategy XIRR:</span>
            <span className={`text-2xl font-mono font-bold ${data.group1.xirr >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {data.group1.xirr ? `${data.group1.xirr.toFixed(2)}%` : 'N/A'}
            </span>
          </div>
        </div>

        {/* GROUP 2: GUPPY FILTERED */}
        <div className="bg-gray-900 border border-emerald-900/50 rounded-lg p-5 flex flex-col justify-between shadow-lg shadow-emerald-950/10">
          <div>
            <div className="flex justify-between items-start">
              <h3 className="text-lg font-semibold text-white">{data.group2.name}</h3>
              <span className="px-2 py-0.5 text-xs font-mono rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                Guppy Stacked
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">Filters for upward-sloping daily/weekly EMA stack before evaluating proximity.</p>
            
            <div className="mt-6 space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Total Invested:</span>
                <span className="text-sm font-mono text-gray-200">${data.group2.invested.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Ending Portfolio Value:</span>
                <span className="text-sm font-mono text-white font-semibold">${Math.round(data.group2.value).toLocaleString()}</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-gray-800 flex justify-between items-baseline">
            <span className="text-sm text-gray-400">Strategy XIRR:</span>
            <span className={`text-2xl font-mono font-bold ${data.group2.xirr >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {data.group2.xirr ? `${data.group2.xirr.toFixed(2)}%` : 'N/A'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}