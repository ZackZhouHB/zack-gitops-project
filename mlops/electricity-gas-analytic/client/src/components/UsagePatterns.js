import React from 'react';
import { Line, Bar, Radar } from 'react-chartjs-2';
import { Clock, Calendar, Zap, Flame, TrendingUp } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadarController, // Correct import for Radar Chart
  RadialLinearScale, // Correct import for Radar Chart
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, BarElement, RadarController, RadialLinearScale, Title, Tooltip, Legend, Filler
);

const ChartContainer = ({ title, children }) => (
    <div className="bg-white p-6 rounded-lg shadow-sm h-full">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">{title}</h3>
        <div className="h-64">{children}</div>
    </div>
);

const HabitCard = ({ icon, title, children }) => {
    const Icon = icon;
    return (
        <div className="bg-white p-5 rounded-lg shadow-sm flex items-start space-x-4">
            <Icon className="h-6 w-6 text-blue-500 mt-1" />
            <div>
                <h4 className="font-semibold text-gray-800">{title}</h4>
                <p className="text-sm text-gray-600">{children}</p>
            </div>
        </div>
    )
}

const UsagePatterns = ({ data }) => {
    if (!data || !data.hourly_avg || !data.weekly_avg || !data.radar_data || !data.peak_times) {
        return (
            <div className="p-8 text-center">
                <p className="text-gray-500">No usage pattern data available</p>
            </div>
        );
    }

    const { hourly_avg, weekly_avg, radar_data, peak_times } = data;

    // --- Chart Configurations --- //
    const lineChartData = { labels: Array.from({ length: 24 }, (_, i) => i), datasets: [{ label: 'Avg. Electricity', data: hourly_avg.electricity || Array(24).fill(0), borderColor: '#3b82f6', tension: 0.3, fill: true, backgroundColor: 'rgba(59, 130, 246, 0.1)' }, { label: 'Avg. Gas', data: hourly_avg.gas || Array(24).fill(0), borderColor: '#10b981', tension: 0.3 }] };
    const barChartData = { labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], datasets: [{ label: 'Electricity', data: weekly_avg.electricity || Array(7).fill(0), backgroundColor: '#3b82f6' }, { label: 'Gas', data: weekly_avg.gas || Array(7).fill(0), backgroundColor: '#10b981' }] };
    const radarChartData = { labels: radar_data.labels || [], datasets: [{ label: 'Electricity', data: radar_data.electricity || [], backgroundColor: 'rgba(59, 130, 246, 0.2)', borderColor: '#3b82f6', pointBackgroundColor: '#3b82f6' }, { label: 'Gas', data: radar_data.gas || [], backgroundColor: 'rgba(16, 185, 129, 0.2)', borderColor: '#10b981', pointBackgroundColor: '#10b981' }] };
    const commonOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 15 } } } };

    return (
        <div className="space-y-8">
            {/* Top Habit Cards */}
            <div className="grid lg:grid-cols-3 gap-6">
                <HabitCard icon={Clock} title="Evening Peak Usage">Peak electricity usage is between 17:00-21:00.</HabitCard>
                <HabitCard icon={Calendar} title="Higher Weekend Usage">Gas usage increases by 15% on weekends.</HabitCard>
                <HabitCard icon={TrendingUp} title="Consistent Night Usage">A baseline of energy is consistently used overnight.</HabitCard>
            </div>

            {/* Main Chart Grid */}
            <div className="grid lg:grid-cols-2 gap-8">
                <ChartContainer title="24-Hour Usage Pattern (Avg. kWh)"><Line data={lineChartData} options={commonOptions} /></ChartContainer>
                <ChartContainer title="One-Week Usage Pattern (Avg. kWh)"><Bar data={barChartData} options={commonOptions} /></ChartContainer>
                <ChartContainer title="Usage Intensity Radar"><Radar data={radarChartData} options={commonOptions} /></ChartContainer>
                
                {/* Peak Usage Times */}
                <div className="bg-white p-6 rounded-lg shadow-sm space-y-4">
                    <h3 className="text-lg font-semibold text-gray-800">Peak Usage Times</h3>
                    <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
                        <div className="flex items-center space-x-3">
                            <Zap className="h-6 w-6 text-blue-600" />
                            <div>
                                <p className="font-semibold text-blue-800">Peak Electricity Time</p>
                                <p className="text-2xl font-bold text-blue-900">{peak_times.electricity?.hour || 0}:00</p>
                                <p className="text-sm text-blue-700">{(peak_times.electricity?.consumption || 0).toFixed(2)} kWh was the highest consumption</p>
                            </div>
                        </div>
                    </div>
                    <div className="bg-green-50 border border-green-200 p-4 rounded-lg">
                        <div className="flex items-center space-x-3">
                            <Flame className="h-6 w-6 text-green-600" />
                            <div>
                                <p className="font-semibold text-green-800">Peak Gas Time</p>
                                <p className="text-2xl font-bold text-green-900">{peak_times.gas?.hour || 0}:00</p>
                                <p className="text-sm text-green-700">{(peak_times.gas?.consumption || 0).toFixed(2)} kWh was the highest consumption</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UsagePatterns;
