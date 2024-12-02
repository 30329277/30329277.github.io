document.addEventListener("DOMContentLoaded", () => {
    const articleList = document.getElementById("article-list");

    // 首页加载文章列表
    if (articleList) {
        fetch("articles.json")
            .then(res => res.json())
            .then(data => {
                const sortedArticles = data.sort((a, b) => new Date(b.date) - new Date(a.date));
                sortedArticles.forEach(article => {
                    const li = document.createElement("li");
                    li.classList.add("article-item");
                    li.innerHTML = `
                        <a href="article.html?id=${article.id}">${article.title}</a>
                        <span class="edit-link"><a href="edit.html?id=${article.id}">编辑文章</a></span>
                        <p>${article.date}</p>
                    `;
                    articleList.appendChild(li);
                });
            });
    }

    // 文章详情页
    const params = new URLSearchParams(window.location.search);
    const articleId = params.get("id");

    if (window.location.pathname.includes("article.html") && articleId) {
        fetch("articles.json")
            .then(res => res.json())
            .then(data => {
                const article = data.find(a => a.id == articleId);
                if (article) {
                    document.getElementById("article-title").innerText = article.title;
                    document.getElementById("article-date").innerText = `发布时间: ${article.date}`;
                    document.getElementById("article-content").innerText = article.content;
                }
            });
    }

    // 编辑页面
    if (window.location.pathname.includes("edit.html") && articleId) {
        const form = document.getElementById("edit-form");
        fetch("articles.json")
            .then(res => res.json())
            .then(data => {
                const article = data.find(a => a.id == articleId);
                if (article) {
                    document.getElementById("title").value = article.title;
                    document.getElementById("content").value = article.content;
                }
            });

        form.addEventListener("submit", (e) => {
            e.preventDefault();
            // 保存功能需要结合后端或本地存储
            alert("文章已保存！（保存功能需后端支持）");
        });
    }
});
