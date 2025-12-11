function setReportMetric(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

window.openScheduleReportModal = function openScheduleReportModal() {
    const modalElement = document.getElementById('scheduleReportModal');
    if (!modalElement) {
        return;
    }

    const modalInstance = bootstrap.Modal.getOrCreateInstance(modalElement);
    modalInstance.show();
};

// Populate default mock statistics until backend data is wired up
window.addEventListener('DOMContentLoaded', () => {
    setReportMetric('monthRevenue', '0 VND');
    setReportMetric('monthExpense', '0 VND');
    setReportMetric('monthProfit', '0 VND');
    setReportMetric('reportsSent', '0');
});
