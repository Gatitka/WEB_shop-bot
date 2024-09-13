document.addEventListener('DOMContentLoaded', function () {
    let displayMode = 'sales';  // Изначально отображаем суммы продаж

    const fetchDataAndRenderChart = () => {
        fetch('/admin/sales-data/')
            .then(response => response.json())
            .then(data => {
                const totalSalesData = data.total_sales;
                const siteSalesData = data.site_sales;
                const botSalesData = data.bot_sales;
                const totalOrdersData = data.total_orders;
                const siteOrdersData = data.site_orders;
                const botOrdersData = data.bot_orders;

                const formatDate = (dateString) => {
                    const date = new Date(dateString);
                    const options = { day: '2-digit', month: '2-digit', year: 'numeric' };
                    return date.toLocaleDateString('en-GB', options);
                };

                const chartCanvas = document.getElementById('salesChart');
                if (!chartCanvas) {
                    console.error('Element with id "salesChart" not found.');
                    return;
                }

                const chartCtx = chartCanvas.getContext('2d');

                const datasets = [
                    {
                        label: 'Total Sales',
                        yAxisID: 'sales',
                        data: totalSalesData.map(item => item.total),
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        type: 'bar',
                    },
                    {
                        label: 'Site Sales',
                        yAxisID: 'sales',
                        data: siteSalesData.map(item => item.total),
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        type: 'line',
                        fill: false,
                    },
                    {
                        label: 'Bot Sales',
                        yAxisID: 'sales',
                        data: botSalesData.map(item => item.total),
                        borderColor: 'rgba(255, 206, 86, 1)',
                        backgroundColor: 'rgba(255, 206, 86, 0.2)',
                        type: 'line',
                        fill: false,
                    }
                ];

                if (displayMode === 'orders') {
                    datasets[0].data = totalOrdersData.map(item => item.total_orders);
                    datasets[0].label = 'Total Orders';
                    datasets[1].data = siteOrdersData.map(item => item.total_orders);
                    datasets[1].label = 'Site Orders';
                    datasets[2].data = botOrdersData.map(item => item.total_orders);
                    datasets[2].label = 'Bot Orders';
                }

                if (window.salesChart instanceof Chart) {
                    window.salesChart.destroy();
                }

                window.salesChart = new Chart(chartCtx, {
                    type: 'bar',
                    data: {
                        labels: totalSalesData.map(item => formatDate(item.day)),
                        datasets: datasets
                    },
                    options: {
                        scales: {
                            yAxes: [{
                                id: 'sales',
                                type: 'linear',
                                position: 'left',
                                scaleLabel: {
                                    display: true,
                                    labelString: displayMode === 'sales' ? 'Sales (Dinars)' : 'Orders',
                                },
                                ticks: {
                                    beginAtZero: true,
                                }
                            }],
                            xAxes: [{
                                ticks: {
                                    callback: function(value, index, values) {
                                        return formatDate(value);
                                    }
                                }
                            }]
                        }
                    }
                });
            })
            .catch(error => {
                console.error('Error fetching sales data:', error);
            });
    };

    document.getElementById('toggleDisplay').addEventListener('click', () => {
        displayMode = displayMode === 'sales' ? 'orders' : 'sales';
        fetchDataAndRenderChart();
    });

    fetchDataAndRenderChart();
});
