(function () {
  if (!localStorage.getItem("proenem_token")) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.replace("/pages/authentication/login.html?next=" + next);
  }
})();
