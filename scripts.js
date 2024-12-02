document.addEventListener("DOMContentLoaded", () => {
    const articleList = document.getElementById("article-list");
    const storageKey = "articles";

    // 初始化文章数据
    const defaultArticles = [
        {
            id: 1,
            title: "第一篇文章",
            content: "这是第一篇文章的内容。",
            date: "2024-12-01"
        },
        {
            id: 2,
            title: "第二篇文章",
            content: "这是第二篇文章的内容。",
            date: "2024-11-30"
        }
    ];

    // 如果 localStorage 没有数据，初始化默认文章
    if (!localStorage.getItem(storageKey)) {
        localStorage.setItem(storageKey, JSON.stringify(defaultArticles));
    }

    // 获取文章数据
    const getArticles = () => {
        return JSON.parse(localStorage.getItem(storageKey)) || [];
    };

    // 保存文章数据
    const saveArticles = (articles) => {
        localStorage.setItem(storageKey, JSON.stringify(articles));
    };

    // 首页加载文章列表
    if (articleList) {
        const articles = getArticles();
        const sortedArticles = articles.sort((a, b) => new Date(b.date) - new Date(a.date));

        sortedArticles.forEach((article) => {
            const li = document.createElement("li");
            li.classList.add("article-item");
            li.innerHTML = `
                <a href="article.html?id=${article.id}">${article.title}</a>
                <span class="edit-link"><a href="edit.html?id=${article.id}">编辑文章</a></span>
                <p>${article.date}</p>
            `;
            articleList.appendChild(li);
        });
    }

    // 文章详情页
    const params = new URLSearchParams(window.location.search);
    const articleId = params.get("id");

    if (window.location.pathname.includes("article.html") && articleId) {
        const articles = getArticles();
        const article = articles.find((a) => a.id == articleId);

        if (article) {
            document.getElementById("article-title").innerText = article.title;
            document.getElementById("article-date").innerText = `发布时间: ${article.date}`;
            document.getElementById("article-content").innerText = article.content;
        }
    }

    // 写新文章页面逻辑
    if (window.location.pathname.includes("new.html")) {
        const form = document.getElementById("new-article-form");

        form.addEventListener("submit", (e) => {
            e.preventDefault();

            // 获取表单数据
            const title = document.getElementById("title").value;
            const content = document.getElementById("content").value;
            const date = new Date().toISOString().split("T")[0];

            // 构造新文章对象
            const newArticle = {
                id: Date.now(),
                title,
                content,
                date
            };

            // 保存到 localStorage
            const articles = getArticles();
            articles.push(newArticle);
            saveArticles(articles);

            alert("文章已发布！");
            window.location.href = "index.html";
        });
    }

    // 编辑文章页面逻辑
    if (window.location.pathname.includes("edit.html") && articleId) {
        const form = document.getElementById("edit-form");
        const articles = getArticles();
        const article = articles.find((a) => a.id == articleId);

        if (article) {
            document.getElementById("title").value = article.title;
            document.getElementById("content").value = article.content;
        }

        form.addEventListener("submit", (e) => {
            e.preventDefault();

            // 更新文章内容
            article.title = document.getElementById("title").value;
            article.content = document.getElementById("content").value;

            saveArticles(articles);

            alert("文章已保存！");
            window.location.href = "index.html";
        });
    }
});
