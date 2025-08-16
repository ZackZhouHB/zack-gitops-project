import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const ChartContainer = ({ title, children }) => (
    <div className="bg-white p-6 rounded-lg shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">{title}</h3>
        <div>{children}</div>
    </div>
);

const ConsumptionTrends = ({ data }) => {
    if (!data || !data.hourly_avg || !data.weekly_avg) {
        return (
            <div className="p-8 text-center">
                <p className="text-gray-500">No consumption data available</p>
            </div>
        );
    }

    // --- Hourly Consumption Chart --- //
    const hourlyLabels = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0') + ':00');
    const hourlyChartData = {
        labels: hourlyLabels,
        datasets: [
            {
                label: 'Gas',
                data: data.hourly_avg.gas || Array(24).fill(0), // Default to 24 zeros if undefined
                backgroundColor: '#2563eb', // Blue
                borderRadius: 4,
            },
            {
                label: 'Electricity',
                data: data.hourly_avg.electricity || Array(24).fill(0), // Default to 24 zeros if undefined
                backgroundColor: '#10b981', // Green
                borderRadius: 4,
            },
        ],
    };
    const hourlyOptions = {
        responsive: true,
        plugins: {
            legend: { position: 'bottom' },
            title: { display: false },
        },
        scales: {
            x: { grid: { display: false } },
            y: { beginAtZero: true },
        },
    };

    // --- Weekly Consumption Chart --- //
    const weeklyLabels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const weeklyChartData = {
        labels: weeklyLabels,
        datasets: [
            {
                label: 'Gas',
                data: data.weekly_avg.gas || Array(7).fill(0), // Default to 7 zeros if undefined
                backgroundColor: '#2563eb',
                borderRadius: 4,
            },
            {
                label: 'Electricity',
                data: data.weekly_avg.electricity || Array(7).fill(0), // Default to 7 zeros if undefined
                backgroundColor: '#10b981',
                borderRadius: 4,
            },
        ],
    };
     const weeklyOptions = {
        responsive: true,
        plugins: {
            legend: { position: 'bottom' },
            title: { display: false },
        },
        scales: {
            x: { stacked: true, grid: { display: false } },
            y: { stacked: true, beginAtZero: true },
        },
    };


    return (
        <div className="space-y-8">
            <ChartContainer title="24-Hour Consumption Pattern">
                <Bar options={hourlyOptions} data={hourlyChartData} />
            </ChartContainer>
            <ChartContainer title="Weekly Consumption Pattern">
                <Bar options={weeklyOptions} data={weeklyChartData} />
            </ChartContainer>
        </div>
    );
};

export default ConsumptionTrends;
