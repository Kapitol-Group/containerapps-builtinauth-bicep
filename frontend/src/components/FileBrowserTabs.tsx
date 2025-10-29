import React from 'react';
import './FileBrowserTabs.css';

export type TabType = 'files' | 'batches';

interface FileBrowserTabsProps {
    activeTab: TabType;
    onTabChange: (tab: TabType) => void;
    filesCount: number;
    batchesCount: number;
    children: React.ReactNode;
}

const FileBrowserTabs: React.FC<FileBrowserTabsProps> = ({
    activeTab,
    onTabChange,
    filesCount,
    batchesCount,
    children,
}) => {
    return (
        <div className="file-browser-tabs">
            <div className="tabs-header">
                <button
                    className={`tab-button ${activeTab === 'files' ? 'active' : ''}`}
                    onClick={() => onTabChange('files')}
                >
                    Active Files
                    <span className="tab-badge">{filesCount}</span>
                </button>
                <button
                    className={`tab-button ${activeTab === 'batches' ? 'active' : ''}`}
                    onClick={() => onTabChange('batches')}
                >
                    Submitted Batches
                    <span className="tab-badge">{batchesCount}</span>
                </button>
            </div>
            <div className="tabs-content">
                {children}
            </div>
        </div>
    );
};

export default FileBrowserTabs;
