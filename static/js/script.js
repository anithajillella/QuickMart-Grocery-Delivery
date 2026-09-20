/* =========================================
   QUICKMART - MAIN JAVASCRIPT
========================================= */


/* =========================================
   CART FUNCTIONS
========================================= */

function getCart() {

    let cart = localStorage.getItem("quickmartCart");

    if (cart) {
        return JSON.parse(cart);
    }

    return [];
}


function saveCart(cart) {

    localStorage.setItem(
        "quickmartCart",
        JSON.stringify(cart)
    );

    updateCartCount();
}


/* =========================================
   UPDATE CART COUNT
========================================= */

function updateCartCount() {

    const cartCount =
        document.getElementById("cartCount");

    if (!cartCount) {
        return;
    }

    const cart = getCart();

    let count = 0;

    cart.forEach(function(item) {
        count += item.quantity;
    });

    cartCount.textContent = count;
}


/* =========================================
   ADD PRODUCT TO CART
========================================= */

function addToCart(id, name, price) {

    let cart = getCart();

    let existingProduct =
        cart.find(function(item) {

            return item.id === id;

        });


    if (existingProduct) {

        existingProduct.quantity += 1;

    } else {

        cart.push({

            id: id,

            name: name,

            price: price,

            quantity: 1

        });
    }


    saveCart(cart);

    alert(name + " added to cart!");
}


/* =========================================
   DISPLAY CART
========================================= */

function displayCart() {

    const cartItems =
        document.getElementById("cartItems");

    const emptyCart =
        document.getElementById("emptyCart");

    const subtotalElement =
        document.getElementById("subtotal");

    const deliveryElement =
        document.getElementById("deliveryFee");

    const totalElement =
        document.getElementById("total");


    if (!cartItems) {
        return;
    }


    const cart = getCart();


    cartItems.innerHTML = "";


    if (cart.length === 0) {

        if (emptyCart) {
            emptyCart.style.display = "block";
        }

        if (subtotalElement) {
            subtotalElement.textContent = "0";
        }

        if (totalElement) {
            totalElement.textContent = "0";
        }

        return;
    }


    if (emptyCart) {
        emptyCart.style.display = "none";
    }


    let subtotal = 0;


    cart.forEach(function(item) {

        const itemTotal =
            item.price * item.quantity;

        subtotal += itemTotal;


        const div =
            document.createElement("div");

        div.className = "cart-item";


        div.innerHTML = `

            <div class="cart-item-info">

                <div class="cart-item-name">
                    ${item.name}
                </div>

                <div class="cart-item-price">
                    ₹${item.price}
                </div>

            </div>


            <div class="quantity-controls">

                <button
                    onclick="decreaseQuantity(${item.id})">
                    −
                </button>

                <span class="quantity">
                    ${item.quantity}
                </span>

                <button
                    onclick="increaseQuantity(${item.id})">
                    +
                </button>

            </div>


            <strong>
                ₹${itemTotal}
            </strong>


            <button
                class="remove-btn"
                onclick="removeFromCart(${item.id})">

                Remove

            </button>
        `;


        cartItems.appendChild(div);

    });


    const deliveryFee = 20;

    const total = subtotal + deliveryFee;


    if (subtotalElement) {
        subtotalElement.textContent =
            subtotal;
    }


    if (deliveryElement) {
        deliveryElement.textContent =
            deliveryFee;
    }


    if (totalElement) {
        totalElement.textContent =
            total;
    }
}


/* =========================================
   INCREASE QUANTITY
========================================= */

function increaseQuantity(id) {

    let cart = getCart();


    const item =
        cart.find(function(product) {

            return product.id === id;

        });


    if (item) {

        item.quantity += 1;

    }


    saveCart(cart);

    displayCart();
}


/* =========================================
   DECREASE QUANTITY
========================================= */

function decreaseQuantity(id) {

    let cart = getCart();


    const item =
        cart.find(function(product) {

            return product.id === id;

        });


    if (item) {

        item.quantity -= 1;


        if (item.quantity <= 0) {

            cart =
                cart.filter(function(product) {

                    return product.id !== id;

                });
        }
    }


    saveCart(cart);

    displayCart();
}


/* =========================================
   REMOVE FROM CART
========================================= */

function removeFromCart(id) {

    let cart = getCart();


    cart =
        cart.filter(function(item) {

            return item.id !== id;

        });


    saveCart(cart);

    displayCart();
}


/* =========================================
   LOAD ALL PRODUCTS
========================================= */

async function loadProducts() {

    try {

        const response =
            await fetch("/api/products");


        if (!response.ok) {

            throw new Error(
                "Failed to load products"
            );

        }


        const products =
            await response.json();


        displayProducts(products);


    } catch (error) {

        console.error(
            "Error loading products:",
            error
        );

    }
}


/* =========================================
   LOAD PRODUCTS BY CATEGORY
========================================= */

async function loadCategory(category) {

    try {

        const response =
            await fetch(
                "/api/products/category/" +
                encodeURIComponent(category)
            );


        if (!response.ok) {

            throw new Error(
                "Failed to load category"
            );

        }


        const products =
            await response.json();


        displayProducts(products);


    } catch (error) {

        console.error(
            "Error loading category:",
            error
        );

    }
}


/* =========================================
   DISPLAY PRODUCTS
========================================= */

function displayProducts(products) {

    const container =
        document.getElementById(
            "productContainer"
        );


    const noProducts =
        document.getElementById(
            "noProducts"
        );


    if (!container) {
        return;
    }


    container.innerHTML = "";


    if (!products || products.length === 0) {

        if (noProducts) {
            noProducts.style.display = "block";
        }

        return;
    }


    if (noProducts) {
        noProducts.style.display = "none";
    }


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
                    '${escapeQuotes(product.name)}',
                    ${product.price}
                )">

                Add to Cart

            </button>
        `;


        container.appendChild(card);

    });
}


/* =========================================
   ESCAPE QUOTES
========================================= */

function escapeQuotes(text) {

    return text
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'");
}


/* =========================================
   SEARCH PRODUCTS
========================================= */

async function searchProducts() {

    const searchBox =
        document.getElementById(
            "searchBox"
        );


    if (!searchBox) {
        return;
    }


    const search =
        searchBox.value.trim();


    if (search === "") {

        loadProducts();

        return;
    }


    try {

        const response =
            await fetch(
                "/api/products/search?q=" +
                encodeURIComponent(search)
            );


        const products =
            await response.json();


        displayProducts(products);


    } catch (error) {

        console.error(
            "Search error:",
            error
        );

    }
}


/* =========================================
   HOME SEARCH
========================================= */

function searchFromHome() {

    const searchInput =
        document.getElementById(
            "homeSearch"
        );


    if (!searchInput) {
        return;
    }


    const search =
        searchInput.value.trim();


    window.location.href =
        "/products?search=" +
        encodeURIComponent(search);
}


/* =========================================
   OPEN CATEGORY
========================================= */

function openCategory(category) {

    window.location.href =
        "/products?category=" +
        encodeURIComponent(category);
}


/* =========================================
   NAVIGATION
========================================= */

function goHome() {

    window.location.href = "/";
}


function goProducts() {

    window.location.href = "/products";
}


function login() {

    window.location.href = "/login";
}


/* =========================================
   CHECKOUT
========================================= */

function proceedToCheckout() {

    const cart = getCart();

    if (cart.length === 0) {

        alert("Your cart is empty.");

        return;
    }

    window.location.href = "/checkout";
}


/* =========================================
   PAGE LOAD
========================================= */

document.addEventListener(
    "DOMContentLoaded",
    function() {

        updateCartCount();

        displayCart();


        const productContainer =
            document.getElementById(
                "productContainer"
            );


        if (productContainer) {

            loadProducts();

        }


        const searchBox =
            document.getElementById(
                "searchBox"
            );


        if (searchBox) {

            searchBox.addEventListener(
                "keyup",
                searchProducts
            );

        }

    }
);