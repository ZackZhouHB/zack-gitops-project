import React, { useState, useRef } from 'react';
import { Zap, Flame, DollarSign, Calendar, Database, CheckCircle, AlertTriangle, UploadCloud } from 'lucide-react';

const StatCard = ({ icon, title, value, unit }) => {
    const Icon = icon;
    return (
        <div className="bg-white p-6 rounded-lg shadow-sm flex items-start space-x-4">
            <div className="bg-blue-100 text-blue-600 p-3 rounded-lg">
                <Icon className="h-6 w-6" />
            </div>
            <div>
                <p className="text-sm text-gray-500">{title}</p>
                <p className="text-2xl font-semibold text-gray-900">{value} <span className="text-lg font-medium text-gray-600">{unit}</span></p>
            </div>
        </div>
    );
};

const UploadBox = ({ icon, title, onFileSelect, selectedFile }) => {
    const Icon = icon;
    const inputRef = useRef(null);

    const handleClick = () => {
        inputRef.current.click();
    };

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            onFileSelect(title, file.name);
        }
    };

    return (
        <div 
            className="border-2 border-dashed border-gray-300 rounded-lg p-8 flex flex-col items-center justify-center text-center hover:border-blue-500 cursor-pointer transition-colors duration-200" 
            onClick={handleClick}
        >
            <input type="file" ref={inputRef} onChange={handleFileChange} className="hidden" accept=".csv" />
            <div className="bg-gray-100 rounded-full p-4 mb-4">
                <Icon className="h-10 w-10 text-gray-500" />
            </div>
            <p className="text-lg font-semibold text-gray-700">{title}</p>
            {selectedFile ? (
                <p className="text-sm text-green-600 font-medium mt-2">{selectedFile}</p>
            ) : (
                <p className="text-sm text-gray-500">Click to upload CSV file</p>
            )}
        </div>
    );
}

const DataOverview = ({ data, onGenerateAnalysis, analysisState }) => {
    const [selectedFiles, setSelectedFiles] = useState({});

    const handleFileSelect = (title, fileName) => {
        setSelectedFiles(prev => ({ ...prev, [title]: fileName }));
    };

    const bothFilesSelected = selectedFiles["Electricity Data"] && selectedFiles["Gas Data"];

    // If there is data, show the full dashboard
    if (data) {
        const { total_consumption_kwh, total_cost_c } = data;
        const total_cost_aud = (total_cost_c.electricity + total_cost_c.gas) / 100;
        const daily_avg_cost = total_cost_aud / 60; // Assuming 60 days

        return (
            <div className="space-y-8">
                <div>
                    <h2 className="text-xl font-semibold text-gray-800 mb-4">Key Metrics</h2>
                    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        <StatCard icon={Zap} title="Total Electricity Consumption" value={total_consumption_kwh.electricity.toFixed(2)} unit="kWh" />
                        <StatCard icon={Flame} title="Total Gas Consumption" value={total_consumption_kwh.gas.toFixed(2)} unit="kWh" />
                        <StatCard icon={DollarSign} title="Total Cost" value={`${total_cost_aud.toFixed(2)}`} unit="" />
                        <StatCard icon={Calendar} title="Daily Average Cost" value={`${daily_avg_cost.toFixed(2)}`} unit="" />
                    </div>
                </div>
                <div>
                    <h2 className="text-xl font-semibold text-gray-800 mb-4">Data Quality Summary</h2>
                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        <StatCard icon={Database} title="Total Data Points" value="1488" unit="" />
                        <StatCard icon={CheckCircle} title="Effective Data" value="98%" unit="" />
                        <StatCard icon={AlertTriangle} title="Anomalies Detected" value="12" unit="" />
                    </div>
                </div>
            </div>
        );
    }

    // If there is no data, show the upload screen
    return (
        <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Get Started</h2>
            <p className="text-gray-600 mb-8">Upload your consumption data to begin the analysis.</p>
            
            <div className="max-w-4xl mx-auto">
                <div className="grid md:grid-cols-2 gap-8">
                    <UploadBox 
                        icon={Zap} 
                        title="Electricity Data" 
                        onFileSelect={handleFileSelect} 
                        selectedFile={selectedFiles["Electricity Data"]}
                    />
                    <UploadBox 
                        icon={Flame} 
                        title="Gas Data" 
                        onFileSelect={handleFileSelect} 
                        selectedFile={selectedFiles["Gas Data"]}
                    />
                </div>
                
                <div className="mt-8">
                    <button 
                        onClick={onGenerateAnalysis}
                        disabled={!bothFilesSelected || analysisState === 'loading'}
                        className="w-full max-w-xs mx-auto bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg shadow-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center space-x-2"
                    >
                        <UploadCloud className="h-5 w-5" />
                        <span>{analysisState === 'loading' ? 'Analyzing...' : 'Generate Analysis'}</span>
                    </button>
                </div>

                {analysisState === 'error' && (
                    <p className="text-red-500 mt-4">There was an error loading the analysis. Please try again.</p>
                )}

                <p className="text-sm text-gray-500 mt-6">Note: File upload is for demonstration purposes. The analysis is based on the pre-loaded data.</p>
            </div>
        </div>
    );
};

export default DataOverview;
