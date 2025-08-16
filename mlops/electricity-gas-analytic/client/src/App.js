import React, { useState } from 'react';
import DataOverview from './components/DataOverview';
import ConsumptionTrends from './components/ConsumptionTrends';
import CostAnalysis from './components/CostAnalysis';
import UsagePatterns from './components/UsagePatterns';
import ProfessionalReport from './components/ProfessionalReport';
import { LayoutDashboard, BarChart3, PieChart, SlidersHorizontal, FileText, Loader } from 'lucide-react';

const TABS = [
    { name: 'Data Overview', slug: 'overview', icon: LayoutDashboard },
    { name: 'Consumption Trends', slug: 'trends', icon: BarChart3 },
    { name: 'Cost Analysis', slug: 'cost', icon: PieChart },
    { name: 'Usage Patterns', slug: 'patterns', icon: SlidersHorizontal },
    { name: 'Professional Report', slug: 'report', icon: FileText },
];

const App = () => {
    const [analysisData, setAnalysisData] = useState(null);
    const [activeTab, setActiveTab] = useState(TABS[0].slug);
    const [analysisState, setAnalysisState] = useState('idle'); // idle, loading, success, error

    const handleGenerateAnalysis = () => {
        setAnalysisState('loading');
        fetch('/analysis_results.json')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                setAnalysisData(data);
                setAnalysisState('success');
            })
            .catch(error => {
                console.error('Error fetching analysis data:', error);
                setAnalysisState('error');
            });
    };

    const renderContent = () => {
        if (analysisState === 'idle' || analysisState === 'error') {
            return <DataOverview data={null} onGenerateAnalysis={handleGenerateAnalysis} analysisState={analysisState} />;
        }

        if (analysisState === 'loading') {
            return (
                <div className="flex flex-col items-center justify-center h-96">
                    <Loader className="animate-spin h-8 w-8 text-gray-500" />
                    <p className="mt-4 text-gray-600">Analyzing data, please wait...</p>
                </div>
            );
        }

        if (analysisState === 'success' && analysisData) {
            switch (activeTab) {
                case 'overview':
                    return <DataOverview data={analysisData.data_overview} onGenerateAnalysis={handleGenerateAnalysis} analysisState={analysisState} />;
                case 'trends':
                    return <ConsumptionTrends data={analysisData.consumption_trends} />;
                case 'cost':
                    return <CostAnalysis data={analysisData.cost_analysis} />;
                case 'patterns':
                    return <UsagePatterns data={analysisData.usage_patterns} />;
                case 'report':
                    return <ProfessionalReport data={analysisData} />;
                default:
                    return null;
            }
        }
        
        return null; // Should not be reached
    };

    return (
        <div className="min-h-screen bg-gray-50 text-gray-800">
            <header className="bg-white shadow-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <h1 className="text-2xl font-semibold text-gray-900">Zack's Electricity & Gas Analysis Platform</h1>
                </div>
                <nav className="border-b border-gray-200">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="flex space-x-8">
                            {TABS.map(tab => {
                                const Icon = tab.icon;
                                const isActive = activeTab === tab.slug;
                                return (
                                    <button
                                        key={tab.slug}
                                        onClick={() => setActiveTab(tab.slug)}
                                        disabled={!analysisData} // Disable tabs if no data
                                        className={`flex items-center space-x-2 px-1 py-4 text-sm font-medium border-b-2 ${
                                            isActive ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'
                                        } ${
                                            !analysisData ? 'cursor-not-allowed text-gray-400' : 'hover:text-gray-700 hover:border-gray-300'
                                        }`}>
                                        <Icon className={`h-5 w-5 ${isActive ? 'text-blue-500' : 'text-gray-400'}`} />
                                        <span>{tab.name}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </nav>
            </header>
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {renderContent()}
            </main>
        </div>
    );
};

export default App;
