/* =========================================
   QUICKMART - PRODUCTS PAGE
========================================= */


/* =========================================
   LOAD PRODUCTS FROM API
========================================= */

async function fetchProducts() {

    try {

        const response =
            await fetch("/api/products");


        if (!response.ok) {

            throw new Error(
                "Unable to fetch products"
            );

        }


        const products =
            await response.json();


        showProducts(products);


    } catch (error) {

        console.error(
            "Product loading error:",
            error
        );

    }
}


/* =========================================
   SHOW PRODUCTS
========================================= */

function showProducts(products) {

    const container =
        document.getElementById(
            "productContainer"
        );


    if (!container) {
        return;
    }


    container.innerHTML = "";


    products.forEach(function(product) {

        const card =
            document.createElement("div");


        card.className = "product";


        card.innerHTML = `

            <div class="product-emoji">
                ${product.emoji || "🛒"}
            </div>

            <h3>
                ${product.name}
            </h3>

            <div class="product-category">
                ${product.category}
            </div>

            <div class="product-price">
                ₹${product.price}
            </div>

            <button
                class="add-cart-btn"
                onclick="addToCart(
                    ${product.id},
                    '${product.name.replace(/'/g, "\\'")}',
                    ${product.price}
                )">

                Add to Cart

            </button>

        `;


        container.appendChild(card);

    });
}


/* =========================================
   CATEGORY FILTER
========================================= */

async function filterProducts(category) {

    try {

        const response =
            await fetch(
                "/api/products/category/" +
                encodeURIComponent(category)
            );


        const products =
            await response.json();


        showProducts(products);


    } catch (error) {

        console.error(
            "Category error:",
            error
        );

    }
}


/* =========================================
   START PRODUCTS PAGE
========================================= */

document.addEventListener(
    "DOMContentLoaded",
    function() {

        const container =
            document.getElementById(
                "productContainer"
            );


        if (container) {

            fetchProducts();

        }

    }
);