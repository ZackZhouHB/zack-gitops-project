import React from 'react';
import { Download, Zap, Flame, DollarSign, Leaf, AlertTriangle, CheckCircle, Settings } from 'lucide-react';

const Section = ({ title, children, ...props }) => (
    <div {...props}>
        <h3 className="text-lg font-semibold text-gray-800 border-b pb-2 mb-4">{title}</h3>
        <div>{children}</div>
    </div>
);

const SummaryStat = ({ icon, label, value, subValue }) => {
    const Icon = icon;
    return (
        <div className="flex items-start space-x-3">
            <Icon className="h-6 w-6 text-gray-500 mt-1" />
            <div>
                <p className="text-gray-600">{label}</p>
                <p className="text-xl font-bold text-gray-900">{value}</p>
                {subValue && <p className="text-sm text-gray-500">{subValue}</p>}
            </div>
        </div>
    );
};

const Recommendation = ({ icon, title, children, saving, color }) => {
    const Icon = icon;
    return (
        <div className="flex items-start space-x-4 py-3 border-b last:border-b-0">
            <Icon className={`h-5 w-5 mt-1 ${color}`} />
            <div className="flex-1">
                <h4 className="font-semibold text-gray-800">{title}</h4>
                <p className="text-sm text-gray-600">{children}</p>
            </div>
            <div className="text-right">
                <p className="font-bold text-green-600">{saving}</p>
                <p className="text-xs text-gray-500">Potential</p>
            </div>
        </div>
    )
}

const ProfessionalReport = ({ data }) => {
    if (!data || !data.data_overview || !data.savings_potential) {
        return (
            <div className="p-8 text-center">
                <p className="text-gray-500">No professional report data available</p>
            </div>
        );
    }

    const { data_overview, savings_potential } = data;
    
    const total_cost = ((data_overview.total_cost_c?.electricity || 0) + (data_overview.total_cost_c?.gas || 0)) / 100;

    const handleExport = () => {
        // A simplified export for demonstration
        alert('Exporting report...');
    }

    return (
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-4xl mx-auto">
            {/* Header */}
            <div className="flex justify-between items-start mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">Professional Analysis Report</h2>
                    <p className="text-sm text-gray-500">Analysis Period: 2025-07-01 - 2025-07-31 (31 days)</p>
                </div>
                <button onClick={handleExport} className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    <Download className="h-4 w-4" />
                    <span>Export Report</span>
                </button>
            </div>

            {/* Score */}
            <div className="bg-gray-50 rounded-lg p-6 flex justify-between items-center mb-8">
                <div>
                    <h3 className="text-lg font-semibold text-gray-800">Energy Score</h3>
                    <p className="text-sm text-gray-600">Comprehensive score based on usage patterns, cost efficiency, and environmental impact.</p>
                </div>
                <div className="text-center">
                    <p className="text-5xl font-bold text-blue-600">70<span className="text-2xl">/100</span></p>
                    <p className="font-semibold text-green-600">Good</p>
                </div>
            </div>

            {/* Summary */}
            <Section title="Execution Summary" className="mb-8">
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <SummaryStat icon={Zap} label="Total Electricity" value={`${(data_overview.total_consumption_kwh?.electricity || 0).toFixed(2)} kWh`} subValue={`${((data_overview.total_cost_c?.electricity || 0) / 100).toFixed(2)}`} />
                    <SummaryStat icon={Flame} label="Total Gas" value={`${(data_overview.total_consumption_kwh?.gas || 0).toFixed(2)} kWh`} subValue={`${((data_overview.total_cost_c?.gas || 0) / 100).toFixed(2)}`} />
                    <SummaryStat icon={DollarSign} label="Total Cost" value={`${total_cost.toFixed(2)}`} subValue={`${(total_cost / 31).toFixed(2)} / day avg`} />
                    <SummaryStat icon={Leaf} label="Carbon Emissions" value="36.82 kg" subValue="Estimated" />
                </div>
            </Section>

            {/* Recommendations */}
            <Section title="Optimization Suggestions">
                <div className="bg-green-50 border-l-4 border-green-500 p-4 mb-6">
                    <p className="font-semibold text-green-800">Total Potential Savings: ${(savings_potential.total_potential_savings || 0).toFixed(2)} per month (15.9% of total cost)</p>
                </div>
                <Recommendation icon={AlertTriangle} title="High Electricity Price" saving="$1.84" color="text-red-500">
                    Your electricity price is relatively high. Consider reviewing your supplier or tariff.
                </Recommendation>
                <Recommendation icon={CheckCircle} title="Good Usage Habits" saving="$1.86" color="text-green-500">
                    Your usage patterns are quite good. Keep up the great work in avoiding peak hours.
                </Recommendation>
                 <Recommendation icon={Settings} title="Device Optimization" saving="$0.95" color="text-yellow-500">
                    Consider upgrading older, less efficient appliances to reduce baseline consumption.
                </Recommendation>
            </Section>
        </div>
    );
};

export default ProfessionalReport;
