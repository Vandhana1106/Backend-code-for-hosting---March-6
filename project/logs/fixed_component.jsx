import React, { useEffect, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { FaTshirt, FaClock, FaTools, FaDownload, FaExclamationTriangle } from "react-icons/fa";
import "./MachineStyles.css";

const MachineReportA = ({ machine_id, fromDate, toDate }) => {
  const [reportData, setReportData] = useState({
    machineId: "",
    totalAvailableHours: 0,
    totalWorkingDays: 0,
    totalHours: 0,
    totalProductiveTime: {
      hours: 0,
      percentage: 0
    },
    totalNonProductiveTime: {
      hours: 0,
      percentage: 0,
      breakdown: {
        noFeedingHours: 0,
        meetingHours: 0,
        maintenanceHours: 0,
        idleHours: 0
      }
    },
    totalStitchCount: 0,
    totalNeedleRuntime: 0,
    tableData: [],
    allTableData: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!machine_id) {
      setError("Machine ID is required");
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const params = new URLSearchParams();
        if (fromDate) params.append('from_date', fromDate);
        if (toDate) params.append('to_date', toDate);

        // Fix URL path - remove redundant 'api/'
        const response = await fetch(`http://127.0.0.1:8000/api/machines/${machine_id}/reports/?${params}`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (!data) {
          throw new Error("No data received from server");
        }

        // Ensure tableData exists and is an array
        const allTableData = Array.isArray(data.tableData) ? data.tableData : [];
        console.log("Received data:", data); // Debug log
        
        setReportData({
          ...data,
          tableData: allTableData,
          allTableData: allTableData,
        });
      } catch (err) {
        console.error("Error fetching machine report:", err);
        setError(err.message || "Failed to load machine report");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [machine_id, fromDate, toDate]);

  const downloadCSV = () => {
    if (!reportData.tableData || reportData.tableData.length === 0) {
      alert("No data available to download");
      return;
    }

    try {
      const headers = Object.keys(reportData.tableData[0] || {});
      const csvRows = [
        headers.join(','),
        ...reportData.tableData.map(row => 
          headers.map(header => 
            `"${row[header] !== undefined ? row[header] : ''}"`
          ).join(',')
        )
      ];
      
      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `machine_${machine_id}_report.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error("Error generating CSV:", err);
      alert("Failed to generate download");
    }
  };

  const downloadHTML = () => {
    if (!reportData.tableData || reportData.tableData.length === 0) {
      alert("No data available to download");
      return;
    }

    try {
      const htmlContent = `<!DOCTYPE html>
        <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .title { text-align: center; }
            .summary { margin-bottom: 20px; }
          </style>
        </head>
        <body>
          <div class="summary">
            <h2>Machine ${machine_id} Report</h2>
            <p>Generated on: ${new Date().toLocaleString()}</p>
            <p>Total Available Hours: ${(reportData.totalAvailableHours || 0).toFixed(2)}</p>
            <p>Productive Time: ${(reportData.totalProductiveTime.hours || 0).toFixed(2)} Hrs</p>
            <p>Non-Productive Time: ${(reportData.totalNonProductiveTime.hours || 0).toFixed(2)} Hrs</p>
          </div>
          <table>
            <thead>
              <tr>
                ${Object.keys(reportData.tableData[0] || {}).map(header => `<th>${header}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${reportData.tableData.map(row => 
                `<tr>
                  ${Object.values(row).map(value => `<td>${value !== undefined ? value : ''}</td>`).join('')}
                </tr>`
              ).join('')}
            </tbody>
          </table>
        </body>
        </html>`;
      
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `machine_${machine_id}_report.html`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error("Error generating HTML:", err);
      alert("Failed to generate download");
    }
  };

  // Chart data with fallback for missing values
  const chartData = [
    { name: "Sewing Hours", value: reportData.totalProductiveTime?.hours || 0, color: "#3E3561" },
    { name: "No Feeding Hours", value: reportData.totalNonProductiveTime?.breakdown?.noFeedingHours || 0, color: "#8E44AD" },
    { name: "Meeting Hours", value: reportData.totalNonProductiveTime?.breakdown?.meetingHours || 0, color: "#E74C3C" },
    { name: "Maintenance Hours", value: reportData.totalNonProductiveTime?.breakdown?.maintenanceHours || 0, color: "#118374" },
    { name: "Idle Hours", value: reportData.totalNonProductiveTime?.breakdown?.idleHours || 0, color: "#F8A723" }
  ].filter(item => item.value > 0);

  if (loading) {
    return (
      <div className="operator-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading machine report...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="operator-container">
        <div className="error-container">
          <FaExclamationTriangle className="error-icon" />
          <h3>Error Loading Report</h3>
          <p>{error}</p>
          <p>Please check the machine ID and try again.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="operator-container">
      <div className="table-section">
        <div className="table-header">
          <h3>Machine {machine_id} Report</h3>
          <div className="table-controls">
            <div className="download-buttons">
              <button onClick={downloadCSV} className="download-button csv" disabled={!reportData.tableData.length}>
                <FaDownload />
              </button>
              <button onClick={downloadHTML} className="download-button html" disabled={!reportData.tableData.length}>
                <FaDownload />
              </button>
            </div>
          </div>
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Sewing Hours (PT)</th>
                <th>No Feeding Hours</th>
                <th>Meeting Hours</th>
                <th>Maintenance Hours</th>
                <th>Idle Hours</th>
                <th>Total Hours</th>
                <th>PT %</th>
                <th>NPT %</th>
                <th>Sewing Speed</th>
                <th>Stitch Count</th>
                <th>Needle Runtime</th>
              </tr>
            </thead>
            <tbody>
              {reportData.tableData.length > 0 ? (
                reportData.tableData.map((row, index) => (
                  <tr key={index}>
                    <td>{row.Date || '-'}</td>
                    <td>{(row["Sewing Hours (PT)"] || 0).toFixed(2)}</td>
                    <td>{(row["No Feeding Hours"] || 0).toFixed(2)}</td>
                    <td>{(row["Meeting Hours"] || 0).toFixed(2)}</td>
                    <td>{(row["Maintenance Hours"] || 0).toFixed(2)}</td>
                    <td>{(row["Idle Hours"] || 0).toFixed(2)}</td>
                    <td>{(row["Total Hours"] || 0).toFixed(2)}</td>
                    <td>{(row["Productive Time (PT) %"] || 0).toFixed(2)}%</td>
                    <td>{(row["Non-Productive Time (NPT) %"] || 0).toFixed(2)}%</td>
                    <td>{(row["Sewing Speed"] || 0).toFixed(2)}</td>
                    <td>{row["Stitch Count"] || 0}</td>
                    <td>{(row["Needle Runtime"] || 0).toFixed(2)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="12" className="no-data">
                    No data available for the selected date range
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {reportData.tableData.length > 0 && (
        <>
          <div className="top-indicators">
            <div className="indicator">
              <h4><FaTshirt /> Total Sewing Hours</h4>
              <p>{(reportData.totalProductiveTime?.hours || 0).toFixed(2)} Hrs</p>
            </div>
            <div className="indicator">
              <h4><FaTools /> Total Non-Productive Hours</h4>
              <p>{(reportData.totalNonProductiveTime?.hours || 0).toFixed(2)} Hrs</p>
            </div>
            <div className="indicator">
              <h4><FaClock /> Total Hours</h4>
              <p>{(reportData.totalHours || 0).toFixed(2)} Hrs</p>
            </div>
          </div>

          <div className="summary-tiles">
            <div className="tile production-percentage">
              <p>{(reportData.totalProductiveTime?.percentage || 0).toFixed(2)}%</p>
              <span>Productive Time</span>
            </div>
            <div className="tile average-speed">
              <p>{
                reportData.tableData.length > 0 
                  ? (reportData.tableData.reduce((sum, row) => sum + (row["Sewing Speed"] || 0), 0) / reportData.tableData.length).toFixed(2)
                  : '0.00'
              }</p>
              <span>Average Sewing Speed</span>
            </div>
          </div>

          <div className="chart-breakdown-container">
            <div className="graph-section">
              <h3>Hours Breakdown (Total: {(reportData.totalHours || 0).toFixed(2)} Hrs)</h3>
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    fill="#8884d8"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value) => `${value.toFixed(2)} Hrs`}
                    labelFormatter={(name) => name || ""}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="hour-breakdown">
              {chartData.map((item) => (
                <div className="hour-box" key={item.name}>
                  <span className="dot" style={{ backgroundColor: item.color }}></span>
                  <p>{item.value.toFixed(2)} Hrs: {item.name}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default MachineReportA;
