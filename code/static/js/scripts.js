function validateForm() {
  const form = document.forms["SurveyForm"];
  const name = form["name"].value.trim();
  const email = form["email"].value.trim();
  const age = form["age"].value.trim();

  if (name === "" || email === "" || age === "") {
    alert("All required fields must be filled!");
    return false;
  }

  const emailPattern = /^[^ ]+@[^ ]+\.[a-z]{2,3}$/;
  if (!emailPattern.test(email)) {
    alert("Please enter a valid email address.");
    return false;
  }

  if (isNaN(age) || age < 15 || age > 100) {
    alert("Please enter a valid age between 15 and 100.");
    return false;
  }

  return true;
}
