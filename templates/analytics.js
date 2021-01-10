//bar
var ctxB = document.getElementById("barChart").getContext('2d');
var myBarChart = new Chart(ctxB, {
type: 'bar',
data: {
labels: ["Red", "Blue", "Yellow"],
datasets: [{
label: 'Tags',
data: [12, 19, 3],
backgroundColor: [
'rgba(255, 99, 132, 0.2)',
'rgba(54, 162, 235, 0.2)',
'rgba(255, 206, 86, 0.2)'
],
borderColor: [
'rgba(255,99,132,1)',
'rgba(54, 162, 235, 1)',
'rgba(255, 206, 86, 1)'
],
borderWidth: 1
}]
},
options: {
    legend: {
    display: false
},
scales: {
yAxes: [{
ticks: {
beginAtZero: true
}
}]
}
}
});