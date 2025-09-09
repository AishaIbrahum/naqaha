// ملف JavaScript (packages.js)
document.addEventListener("DOMContentLoaded", () => {
  const cards = document.querySelectorAll(".package-card");
  const modal = document.getElementById("packageModal");
  const modalTitle = document.getElementById("modalTitle");
  const modalDesc = document.getElementById("modalDesc");
  const closeBtn = document.querySelector(".close");

  // البيانات الخاصة بالباقات
  const packagesData = {
    "باقة التجميل": "تشمل استشارات تجميلية، جراحة بسيطة، وإقامة فندقية.",
    "باقة القلب": "فحوصات شاملة للقلب، استشارة مع أفضل أطباء القلب، وبرنامج تأهيلي.",
    "باقة العظام": "تشمل فحوصات العظام، علاج طبيعي، وخدمات ما بعد العملية.",
    "باقة العيون": "تشمل فحوصات دقيقة للعين وعملية تصحيح النظر.",
    "باقة الاستجمام": "رحلة علاجية متكاملة تشمل الينابيع الحارة وبرامج صحية."
  };

  // عند الضغط على أي بطاقة
  cards.forEach(card => {
    card.addEventListener("click", () => {
      const title = card.querySelector("h2").innerText;
      modalTitle.innerText = title;
      modalDesc.innerText = packagesData[title];
      modal.style.display = "flex";
    });
  });

  // إغلاق المودال
  closeBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });

  // إغلاق عند الضغط خارج المودال
  window.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.style.display = "none";
    }
  });
});