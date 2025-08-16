import React from 'react';
import { Pie, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { DollarSign, Zap, Flame, ArrowDownCircle, Settings, Activity, Info } from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const StatCard = ({ icon, title, value, unit }) => {
    const Icon = icon;
    return (
        <div className="bg-white p-4 rounded-lg shadow-sm flex items-center space-x-3">
            <div className="bg-gray-100 text-gray-600 p-2 rounded-lg">
                <Icon className="h-5 w-5" />
            </div>
            <div>
                <p className="text-sm text-gray-500">{title}</p>
                <p className="text-xl font-semibold text-gray-800">{value} <span className="text-base font-medium">{unit}</span></p>
            </div>
        </div>
    );
};

const ChartContainer = ({ title, children }) => (
    <div className="bg-white p-6 rounded-lg shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">{title}</h3>
        <div>{children}</div>
    </div>
);

const SuggestionCard = ({ icon, title, children, difficulty, color }) => {
    const Icon = icon;
    return (
        <div className="bg-white p-5 rounded-lg shadow-sm">
            <div className="flex items-center space-x-3 mb-2">
                <Icon className={`h-5 w-5 ${color}`} />
                <h4 className="font-semibold text-gray-800">{title}</h4>
            </div>
            <p className="text-sm text-gray-600 mb-3">{children}</p>
            <div className="text-xs text-gray-500">Difficulty: <span className="font-medium">{difficulty}</span></div>
        </div>
    )
}

const CostAnalysis = ({ data }) => {
    if (!data || !data.cost_composition_c || !data.daily_cost_trend) {
        return (
            <div className="p-8 text-center">
                <p className="text-gray-500">No cost analysis data available</p>
            </div>
        );
    }

    const { cost_composition_c, daily_cost_trend } = data;
    const total_cost = ((cost_composition_c.electricity || 0) + (cost_composition_c.gas || 0)) / 100;

    // --- Pie Chart --- //
    const pieChartData = {
        labels: ['Electricity', 'Gas'],
        datasets: [{
            data: [cost_composition_c.electricity || 0, cost_composition_c.gas || 0],
            backgroundColor: ['#3b82f6', '#10b981'],
            borderColor: '#ffffff',
            borderWidth: 2,
        }],
    };
    const pieOptions = { responsive: true, plugins: { legend: { display: false } } };

    // --- Line Chart --- //
    const lineChartData = {
        labels: daily_cost_trend.labels, // Expects an array of dates
        datasets: [
            { label: 'Total Cost', data: daily_cost_trend.total, borderColor: '#f97316', tension: 0.2, pointRadius: 0 },
            { label: 'Gas Cost', data: daily_cost_trend.gas, borderColor: '#10b981', tension: 0.2, pointRadius: 0 },
            { label: 'Electricity Cost', data: daily_cost_trend.electricity, borderColor: '#3b82f6', tension: 0.2, pointRadius: 0 },
        ]
    };
    const lineOptions = { responsive: true, plugins: { legend: { position: 'bottom' } }, scales: { x: { grid: { display: false } } } };

    return (
        <div className="space-y-8">
            {/* Top Metrics */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard icon={DollarSign} title="Total Cost" value={`${total_cost.toFixed(2)}`} />
                <StatCard icon={Zap} title="Electricity Price" value="$0.25" unit="/kWh" />
                <StatCard icon={Flame} title="Gas Price" value="$0.06" unit="/kWh" />
                <StatCard icon={ArrowDownCircle} title="Savings Potential" value="$0.41" />
            </div>

            {/* Charts */}
            <div className="grid lg:grid-cols-5 gap-8">
                <div className="lg:col-span-2">
                    <ChartContainer title="Cost Composition">
                        <div className="w-full max-w-xs mx-auto">
                            <Pie data={pieChartData} options={pieOptions} />
                        </div>
                        <div className="mt-4 flex justify-center space-x-6 text-sm">
                            <div className="flex items-center"><span className="inline-block w-3 h-3 bg-blue-500 rounded-full mr-2"></span>Electricity: ${((cost_composition_c.electricity || 0) / 100).toFixed(2)}</div>
                            <div className="flex items-center"><span className="inline-block w-3 h-3 bg-green-500 rounded-full mr-2"></span>Gas: ${((cost_composition_c.gas || 0) / 100).toFixed(2)}</div>
                        </div>
                    </ChartContainer>
                </div>
                <div className="lg:col-span-3">
                    <ChartContainer title="Daily Cost Trend">
                        <Line data={lineChartData} options={lineOptions} />
                    </ChartContainer>
                </div>
            </div>

            {/* Suggestions */}
            <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Savings Suggestions</h3>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    <SuggestionCard icon={Info} title="Shift Peak Usage" difficulty="Medium" color="text-yellow-500">
                        Shift high-usage appliance use to off-peak hours.
                    </SuggestionCard>
                    <SuggestionCard icon={Settings} title="Device Optimization" difficulty="Hard" color="text-red-500">
                        Upgrade to more energy-efficient devices.
                    </SuggestionCard>
                    <SuggestionCard icon={Activity} title="Behavior Adjustment" difficulty="Easy" color="text-green-500">
                        Optimize daily energy usage habits.
                    </SuggestionCard>
                </div>
            </div>
        </div>
    );
};

export default CostAnalysis;
