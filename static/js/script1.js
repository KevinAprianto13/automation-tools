$(document).ready(function(){
    $("#startBtn").click(function(){
        $("#startBtn").prop('disabled', true);
        $("#resultContainer").show();

        function startSpeedTest() {
            var secondsRemaining = 30;
            var countdownInterval = setInterval(function() {
                secondsRemaining--;
                if (secondsRemaining <= 0) {
                    clearInterval(countdownInterval);
                    $("#startBtn").prop('disabled', false);
                    $("#downloadSpeed").text("Pengujian selesai.");
                }
            }, 1000);

            var speedUpdateInterval = setInterval(function() {
                $.get("/speedtest", function(data) {
                    if ("download_speed" in data) {
                        $("#downloadSpeed").text(data.download_speed.toFixed(2) + " Mbps");
                        $("#uploadSpeed").text(data.upload_speed.toFixed(2) + " Mbps");
                        $("#pingLatency").text(data.ping_latency.toFixed(2) + " ms");

            // Perbarui nilai speedometer dengan kecepatan unduh baru
            speedometer.refresh(data.download_speed);
        } else if ("message" in data) {
            clearInterval(speedUpdateInterval);
            clearInterval(countdownInterval);
            $("#startBtn").prop('disabled', false);
            $("#downloadSpeed").text(data.message);
        }
    }).fail(function() {
        clearInterval(speedUpdateInterval);
        clearInterval(countdownInterval);
        $("#startBtn").prop('disabled', false);
        $("#downloadSpeed").text("Gagal mengambil data pengujian.");
    });
}, 1000);

        }

        startSpeedTest();
    });
});

var speedometer = new JustGage({
    id: "speedometer",
    value: 0,
    min: 0,
    max: 100, // Nilai maksimum speedometer (dalam contoh ini, 100 Mbps)
    title: "Kecepatan",
    label: "Mbps",
    pointer: true,
    pointerOptions: {
        toplength: 10,
        bottomlength: 10,
        bottomwidth: 8,
        color: "#8e8e93",
        stroke: "#ffffff",
        stroke_width: 3,
        stroke_linecap: "round"
    },
    gaugeWidthScale: 0.6,
    counter: true,
    relativeGaugeSize: true,
    donut: true
});