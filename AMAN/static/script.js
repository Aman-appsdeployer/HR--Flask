document.addEventListener("DOMContentLoaded", function() {
    var generateSalaryButton = document.getElementById("generateSalaryButton");
    generateSalaryButton.addEventListener("click", function() {
        // sssssssss
        fetch('/generate_salary', {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            // Handle the response or perform any additional actions
            // For example, you can display a success message or refresh the page
            location.reload(); // Reload the page to see updated salary values
        })
        .catch(error => {
            console.error('Error generating salary:', error);
        });
    });
});
