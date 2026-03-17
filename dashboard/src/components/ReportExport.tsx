/**
 * ReportExport Component
 * 
 * Provides comprehensive report export functionality with format selection and section customization.
 * Requirements: 24.5, 24.6, 24.7, 24.8, 24.9, 24.10
 */

import { useState } from 'react';
import type { ReportFormat, ReportExportRequest } from '../types';
import { exportReport } from '../services/api';

export default function ReportExport() {
  const [isOpen, setIsOpen] = useState(false);
  const [format, setFormat] = useState<ReportFormat>('json');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [sections, setSections] = useState({
    performanceMetrics: true,
    charts: true,
    tradeJournal: true,
  });
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSectionToggle = (section: keyof typeof sections) => {
    setSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const handleExport = async () => {
    try {
      setIsExporting(true);
      setError(null);

      // Validate dates
      if (startDate && endDate && new Date(startDate) > new Date(endDate)) {
        setError('Start date must be before end date');
        return;
      }

      // Validate at least one section selected
      if (!sections.performanceMetrics && !sections.charts && !sections.tradeJournal) {
        setError('Please select at least one section to export');
        return;
      }

      // Prepare request
      const request: ReportExportRequest = {
        format,
        startDate: startDate || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        endDate: endDate || new Date().toISOString().split('T')[0],
        sections,
      };

      // Call export API
      const blob = await exportReport(request);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const timestamp = new Date().toISOString().split('T')[0];
      link.download = `openclaw_report_${timestamp}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      // Close dialog
      setIsOpen(false);
      setStartDate('');
      setEndDate('');
      setSections({
        performanceMetrics: true,
        charts: true,
        tradeJournal: true,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <>
      {/* Export Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-medium"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        Export Report
      </button>

      {/* Export Dialog */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-lg max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold">Export Performance Report</h2>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}

            <div className="space-y-6">
              {/* Format Selection */}
              <div>
                <label className="block text-sm font-medium mb-3">Export Format</label>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    onClick={() => setFormat('json')}
                    className={`px-4 py-3 rounded-lg border-2 transition-colors ${
                      format === 'json'
                        ? 'border-blue-500 bg-blue-500/20 text-blue-400'
                        : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    <div className="font-semibold">JSON</div>
                    <div className="text-xs mt-1">Data format</div>
                  </button>
                  <button
                    onClick={() => setFormat('csv')}
                    className={`px-4 py-3 rounded-lg border-2 transition-colors ${
                      format === 'csv'
                        ? 'border-blue-500 bg-blue-500/20 text-blue-400'
                        : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    <div className="font-semibold">CSV</div>
                    <div className="text-xs mt-1">Spreadsheet</div>
                  </button>
                  <button
                    onClick={() => setFormat('pdf')}
                    className={`px-4 py-3 rounded-lg border-2 transition-colors ${
                      format === 'pdf'
                        ? 'border-blue-500 bg-blue-500/20 text-blue-400'
                        : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    <div className="font-semibold">PDF</div>
                    <div className="text-xs mt-1">Document</div>
                  </button>
                </div>
              </div>

              {/* Date Range */}
              <div>
                <label className="block text-sm font-medium mb-3">Date Range</label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Start Date</label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">End Date</label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Leave empty to use last 30 days
                </p>
              </div>

              {/* Section Selection */}
              <div>
                <label className="block text-sm font-medium mb-3">Report Sections</label>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors">
                    <input
                      type="checkbox"
                      checked={sections.performanceMetrics}
                      onChange={() => handleSectionToggle('performanceMetrics')}
                      className="w-5 h-5 rounded border-gray-700 bg-gray-900 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <div className="font-medium">Performance Metrics</div>
                      <div className="text-xs text-gray-400 mt-1">
                        Win rate, profit factor, Sharpe ratio, drawdown, and more
                      </div>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors">
                    <input
                      type="checkbox"
                      checked={sections.charts}
                      onChange={() => handleSectionToggle('charts')}
                      className="w-5 h-5 rounded border-gray-700 bg-gray-900 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <div className="font-medium">Charts & Visualizations</div>
                      <div className="text-xs text-gray-400 mt-1">
                        Equity curve, PnL breakdown, symbol performance, and quality analysis
                      </div>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors">
                    <input
                      type="checkbox"
                      checked={sections.tradeJournal}
                      onChange={() => handleSectionToggle('tradeJournal')}
                      className="w-5 h-5 rounded border-gray-700 bg-gray-900 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <div className="font-medium">Trade Journal</div>
                      <div className="text-xs text-gray-400 mt-1">
                        Complete trade history with entry/exit details and feature contributions
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Export Info */}
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="text-sm text-gray-400">
                    <p className="mb-2">
                      The report will include all selected sections with comprehensive data and analysis.
                    </p>
                    <ul className="list-disc list-inside space-y-1 text-xs">
                      <li>JSON format includes raw data for further analysis</li>
                      <li>CSV format is optimized for spreadsheet applications</li>
                      <li>PDF format provides a formatted document with charts</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setIsOpen(false)}
                  className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
                  disabled={isExporting}
                >
                  Cancel
                </button>
                <button
                  onClick={handleExport}
                  disabled={isExporting}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isExporting ? (
                    <>
                      <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Generating Report...
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Export Report
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
