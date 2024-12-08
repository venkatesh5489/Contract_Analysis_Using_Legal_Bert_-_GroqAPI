// app/dashboard/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { StatCard } from '@/components/dashboard/StatCard';
import { ActivityList } from '@/components/dashboard/ActivityList';
import { AnalyticsChart } from '@/components/dashboard/AnalyticsChart';
import { api } from '@/lib/api';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [statsData, activityData] = await Promise.all([
          api.get('/admin/statistics'),
          api.get('/admin/recent-activity')
        ]);
        setStats(statsData.data);
        setActivity(activityData.data.recent_activity);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (isLoading) {
    return <LoadingSpinner size="lg" />;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-8">Admin Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Documents"
          value={stats?.total_documents || 0}
          icon="Document"
        />
        <StatCard
          title="Total Comparisons"
          value={stats?.total_comparisons || 0}
          icon="GitCompare"
        />
        <StatCard
          title="Average Match %"
          value={`${stats?.average_match_percentage.toFixed(1)}%` || '0%'}
          icon="PieChart"
        />
        <StatCard
          title="Average Risk Score"
          value={`${stats?.average_risk_score.toFixed(1)}` || '0'}
          icon="AlertTriangle"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
          <ActivityList activities={activity} />
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">Analysis Metrics</h2>
          <AnalyticsChart data={stats?.document_distribution || {}} />
        </Card>
      </div>
    </div>
  );
}