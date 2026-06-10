"use client";

import { useState } from "react";

interface VerificationResult {
  field: string;
  expected: string;
  actual: string;
  status: "PASS" | "FAIL" | "WARNING";
  confidence: number;
  message: string;
}

interface AnalysisResponse {
  filename: string;
  overall_status: string;
  results: VerificationResult[];
  extracted_text: string;
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [brandName, setBrandName] = useState("OLD TOM DISTILLERY");
  const [abv, setAbv] = useState("45%");
  const [warning, setWarning] = useState(
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems."
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [batchFiles, setBatchFiles] = useState<FileList | null>(null);
  const [batchResults, setBatchResults] = useState<AnalysisResponse[]>([]);

  const handleSingleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("brand_name", brandName);
    formData.append("abv", abv);
    formData.append("government_warning", warning);

    try {
      const response = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error("Error:", error);
      alert("Failed to analyze label. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const handleBatchUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!batchFiles || batchFiles.length === 0) return;

    setLoading(true);
    const results: AnalysisResponse[] = [];

    for (let i = 0; i < batchFiles.length; i++) {
      const formData = new FormData();
      formData.append("file", batchFiles[i]);
      formData.append("brand_name", brandName); // For prototype, same data
      formData.append("abv", abv);
      formData.append("government_warning", warning);

      try {
        const response = await fetch("http://localhost:8000/analyze", {
          method: "POST",
          body: formData,
        });
        const data = await response.json();
        results.push(data);
      } catch (error) {
        console.error("Error:", error);
      }
    }

    setBatchResults(results);
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-gray-50 p-8 text-gray-900">
      <div className="max-w-4xl mx-auto">
        <header className="mb-12 text-center">
          <h1 className="text-4xl font-bold text-blue-900 mb-2">
            TTB AI Label Verifier
          </h1>
          <p className="text-gray-600">
            Speeding up compliance review with AI matching.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
          {/* Application Data Form */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h2 className="text-xl font-semibold mb-4 border-b pb-2">
              Application Details
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Brand Name
                </label>
                <input
                  type="text"
                  value={brandName}
                  onChange={(e) => setBrandName(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  ABV / Proof
                </label>
                <input
                  type="text"
                  value={abv}
                  onChange={(e) => setAbv(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Government Warning
                </label>
                <textarea
                  value={warning}
                  onChange={(e) => setWarning(e.target.value)}
                  rows={4}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
          </div>

          {/* Upload Section */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h2 className="text-xl font-semibold mb-4 border-b pb-2">
              Upload Label(s)
            </h2>
            <div className="space-y-8">
              <form onSubmit={handleSingleUpload} className="space-y-4">
                <h3 className="font-medium text-blue-800">Single Label Check</h3>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                <button
                  type="submit"
                  disabled={loading || !file}
                  className="w-full bg-blue-600 text-white py-2 px-4 rounded-md font-semibold hover:bg-blue-700 disabled:bg-gray-400 transition"
                >
                  {loading ? "Analyzing..." : "Analyze Single"}
                </button>
              </form>

              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-gray-200"></span>
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-white px-2 text-gray-500 font-bold">OR</span>
                </div>
              </div>

              <form onSubmit={handleBatchUpload} className="space-y-4">
                <h3 className="font-medium text-purple-800">Batch Upload</h3>
                <input
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={(e) => setBatchFiles(e.target.files)}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
                />
                <button
                  type="submit"
                  disabled={loading || !batchFiles}
                  className="w-full bg-purple-600 text-white py-2 px-4 rounded-md font-semibold hover:bg-purple-700 disabled:bg-gray-400 transition"
                >
                  {loading ? "Processing Batch..." : "Start Batch Analysis"}
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Results Section */}
        {result && (
          <div className="bg-white p-6 rounded-xl shadow-md border-t-4 border-blue-600 mb-8 animation-fade-in">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">Verification Results</h2>
              <span
                className={`px-4 py-1 rounded-full font-bold text-lg ${
                  result.overall_status === "PASS"
                    ? "bg-green-100 text-green-800"
                    : result.overall_status === "WARNING"
                    ? "bg-yellow-100 text-yellow-800"
                    : "bg-red-100 text-red-800"
                }`}
              >
                {result.overall_status}
              </span>
            </div>

            <div className="space-y-4">
              {result.results.map((res, i) => (
                <div
                  key={i}
                  className="flex flex-col md:flex-row md:items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div className="flex-1">
                    <h4 className="font-bold text-gray-700">{res.field}</h4>
                    <p className="text-sm text-gray-500">
                      Expected: <span className="text-gray-900">{res.expected}</span>
                    </p>
                    <p className="text-sm text-gray-500">
                      Actual: <span className="text-gray-900 italic">"{res.actual}"</span>
                    </p>
                  </div>
                  <div className="mt-2 md:mt-0 flex items-center gap-4">
                    <p className="text-xs text-gray-400">{res.message}</p>
                    <span
                      className={`min-w-20 text-center px-3 py-1 rounded font-bold ${
                        res.status === "PASS"
                          ? "bg-green-500 text-white"
                          : res.status === "WARNING"
                          ? "bg-yellow-500 text-white"
                          : "bg-red-500 text-white"
                      }`}
                    >
                      {res.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8">
              <h3 className="font-semibold mb-2 text-gray-600 uppercase text-xs tracking-wider">
                Extracted Text (Debug)
              </h3>
              <div className="p-3 bg-gray-900 text-green-400 font-mono text-xs rounded-md h-32 overflow-y-auto">
                {result.extracted_text}
              </div>
            </div>
          </div>
        )}

        {/* Batch Results Table */}
        {batchResults.length > 0 && (
          <div className="bg-white p-6 rounded-xl shadow-md border-t-4 border-purple-600 mb-8">
            <h2 className="text-2xl font-bold mb-6">Batch Results ({batchResults.length} files)</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Filename</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Discrepancies</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {batchResults.map((br, i) => (
                    <tr key={i}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{br.filename}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                          br.overall_status === 'PASS' ? 'bg-green-100 text-green-800' :
                          br.overall_status === 'WARNING' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {br.overall_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {br.results.filter(r => r.status !== 'PASS').map(r => r.field).join(', ') || 'None'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
