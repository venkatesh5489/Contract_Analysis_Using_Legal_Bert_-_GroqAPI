'use client';

import { useEffect, useState } from 'react';
import { adminService } from '@/services/api';
import { RiskScoreWidget } from '@/components/analysis/RiskScoreWidget';
import { formatPercentage, formatDate } from '@/utils/transformers';

interface Statistics {
  total_documents: number;
  total_comparisons: number;
  recent_documents: number;
  average_match_percentage: number;
  average_risk_score: number;
  document_distribution: {
    [key: string]: number;
  };
}

interface RecentActivity {
  type: string;
  date: string;
  source_document: string;
  target_document: string;
  match_percentage: number;
  risk_score: number;
}

interface HighRiskContract {
  comparison_id: string;
  source_document: string;
  target_document: string;
  risk_score: number;
  comparison_date: string;
}

export default function AdminDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Statistics | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [highRiskContracts, setHighRiskContracts] = useState<HighRiskContract[]>([]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [statsData, activityData, riskData] = await Promise.all([
          adminService.getStatistics(),
          adminService.getRecentActivity(),
          adminService.getHighRiskContracts(),
        ]);

        setStats(statsData);
        setRecentActivity(activityData.recent_activity);
        setHighRiskContracts(riskData.high_risk_contracts);
      } catch (err) {
        setError('Failed to load dashboard data. Please try again.');
        console.error('Dashboard error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-800">Admin Dashboard</h1>
          <p className="mt-2 text-gray-600">
            System overview and performance metrics
          </p>
        </div>

        {/* Statistics Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Total Documents</h3>
            <p className="text-3xl font-bold text-blue-600">{stats?.total_documents}</p>
            <p className="text-sm text-gray-600 mt-2">
              {stats?.recent_documents} in last 24h
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Total Comparisons</h3>
            <p className="text-3xl font-bold text-blue-600">{stats?.total_comparisons}</p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Average Match Rate</h3>
            <p className="text-3xl font-bold text-green-600">
              {formatPercentage(stats?.average_match_percentage || 0)}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-4">Average Risk Score</h3>
            <RiskScoreWidget
              score={stats?.average_risk_score || 0}
              size="small"
            />
          </div>
        </div>

        {/* High Risk Contracts */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">High Risk Contracts</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                    Source Document
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                    Target Document
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                    Risk Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                    Date
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {highRiskContracts.map((contract, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                      {contract.source_document}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                      {contract.target_document}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                        {formatPercentage(contract.risk_score)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {formatDate(contract.comparison_date)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Recent Activity</h2>
          <div className="space-y-4">
            {recentActivity.map((activity, index) => (
              <div
                key={index}
                className="flex items-center justify-between border-b border-gray-100 pb-4 last:border-0 last:pb-0 hover:bg-gray-50"
              >
                <div>
                  <p className="text-sm text-gray-700">
                    Compared {activity.source_document} with {activity.target_document}
                  </p>
                  <p className="text-xs text-gray-600 mt-1">
                    {formatDate(activity.date)}
                  </p>
                </div>
                <div className="flex items-center space-x-4">
                  <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                    {formatPercentage(activity.match_percentage)} Match
                  </span>
                  <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                    {formatPercentage(activity.risk_score)} Risk
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
} 