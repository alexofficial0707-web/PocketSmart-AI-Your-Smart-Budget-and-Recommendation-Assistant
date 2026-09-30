const $ = (id) =>
    document.getElementById(id);


async function api(
    url,
    options = {}
) {

    const response = await fetch(
        url,
        {
            credentials: "include",
            ...options
        }
    );


    const data =
        await response
            .json()
            .catch(() => ({}));


    if (!response.ok) {

        throw new Error(
            data.detail ||
            "Something went wrong"
        );
    }


    return data;
}


// ============================================================
// SHOW PANEL
// ============================================================

function showPanel(id) {

    document
        .querySelectorAll(".panel")
        .forEach(
            panel =>
                panel.classList.add(
                    "hidden"
                )
        );


    $(id).classList.remove(
        "hidden"
    );


    $("result").innerHTML = "";


    if (id === "historyPanel") {

        loadHistory();

    }

}


// ============================================================
// REGISTER
// ============================================================

async function registerUser() {

    try {

        await api(
            "/api/register",
            {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({

                    username:
                        $("registerUsername")
                            .value,

                    email:
                        $("registerEmail")
                            .value,

                    full_name:
                        $("registerName")
                            .value,

                    password:
                        $("registerPassword")
                            .value

                })

            }
        );


        alert(
            "Account created successfully!"
        );


        location.reload();

    }
    catch (error) {

        alert(
            error.message
        );

    }

}


// ============================================================
// LOGIN
// ============================================================

async function loginUser() {

    try {

        await api(
            "/api/login",
            {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({

                    username:
                        $("loginUsername")
                            .value,

                    password:
                        $("loginPassword")
                            .value

                })

            }
        );


        location.reload();

    }
    catch (error) {

        alert(
            error.message
        );

    }

}


// ============================================================
// LOGOUT
// ============================================================

async function logoutUser() {

    await api(
        "/api/logout",
        {
            method: "POST"
        }
    );

    location.reload();

}


// ============================================================
// HOME BUDGET
// ============================================================

async function generateHome() {

    try {

        const data = {

            total_budget:
                Number(
                    $("homeBudget").value
                ),

            num_lights:
                Number(
                    $("homeLights").value
                ),

            num_fans:
                Number(
                    $("homeFans").value
                ),

            num_furniture:
                Number(
                    $("homeFurniture").value
                ),

            num_dining_tables:
                Number(
                    $("homeTables").value
                ),

            has_living_room:
                $("livingRoom").checked,

            has_kitchen:
                $("kitchen").checked,

            has_bedroom:
                $("bedroom").checked,

            additional_requirements:
                $("homeRequirements")
                    .value
        };


        const result =
            await api(
                "/api/home",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            data
                        )

                }
            );


        displayResult(
            result
        );

    }
    catch (error) {

        alert(
            error.message
        );

    }

}


// ============================================================
// PARTY BUDGET
// ============================================================

async function generateParty() {

    try {

        const needsText =
            $("partyNeeds")
                .value;


        const data = {

            total_budget:
                Number(
                    $("partyBudget")
                        .value
                ),

            occasion:
                $("partyOccasion")
                    .value,

            num_guests:
                Number(
                    $("partyGuests")
                        .value
                ),

            party_type:
                $("partyType")
                    .value,

            needs:
                needsText
                    .split(",")
                    .map(
                        item =>
                            item.trim()
                    )
                    .filter(
                        item =>
                            item.length > 0
                    ),

            additional_requirements:
                needsText

        };


        const result =
            await api(
                "/api/party",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            data
                        )

                }
            );


        displayResult(
            result
        );

    }
    catch (error) {

        alert(
            error.message
        );

    }

}


// ============================================================
// JEWELRY
// ============================================================

async function generateJewelry() {

    try {

        const formData =
            new FormData();


        formData.append(
            "total_budget",
            $("jewelryBudget")
                .value
        );


        formData.append(
            "occasion",
            $("jewelryOccasion")
                .value
        );


        formData.append(
            "preferences",
            $("jewelryPreferences")
                .value
        );


        const image =
            $("outfitImage")
                .files[0];


        if (image) {

            formData.append(
                "image",
                image
            );

        }


        const result =
            await api(
                "/api/jewelry",
                {

                    method: "POST",

                    body:
                        formData

                }
            );


        displayResult(
            result
        );

    }
    catch (error) {

        alert(
            error.message
        );

    }

}


// ============================================================
// DISPLAY RESULT
// ============================================================

function displayResult(
    data
) {

    let html = `

        <div class="result">

            <h2>
                Recommendation
            </h2>

            <p>

                <b>Total Budget:</b>
                ₹${Number(
                    data.total_budget
                ).toLocaleString("en-IN")}

            </p>


            <p>

                <b>Remaining:</b>
                ₹${Number(
                    data.remaining_budget
                ).toLocaleString("en-IN")}

            </p>


            <p>

                <b>AI Source:</b>
                ${data.source}

            </p>

    `;


    const categories =
        data.budget_breakdown ||
        [];


    categories.forEach(
        category => {

            html += `

                <div class="card">

                    <h3>
                        ${category.category}
                    </h3>

                    <p>
                        Category Cost:
                        ₹${Number(
                            category.allocation ||
                            0
                        ).toLocaleString(
                            "en-IN"
                        )}
                    </p>

            `;


            const items =
                category.items ||
                [];


            items.forEach(
                item => {

                    html += `

                        <div class="item">

                            <h4>
                                ${item.name}
                            </h4>

                            <p>
                                ${item.description}
                            </p>

                            <p>
                                Quantity:
                                ${item.quantity}
                            </p>

                            <p>
                                Price:
                                ₹${Number(
                                    item.estimated_price
                                ).toLocaleString(
                                    "en-IN"
                                )}
                            </p>

                    `;


                    const links =
                        item.shopping_links ||
                        {};


                    for (
                        const [platform, url]
                        of Object.entries(
                            links
                        )
                    ) {

                        html += `

                            <a
                                href="${url}"
                                target="_blank"
                            >
                                ${platform}
                            </a>

                        `;

                    }


                    html += `

                        </div>

                    `;

                }
            );


            html += `

                </div>

            `;

        }
    );


    if (
        data.venue_suggestions
    ) {

        html += `

            <div class="card">

                <h3>
                    Venue Suggestions
                </h3>

        `;


        data.venue_suggestions
            .forEach(
                venue => {

                    html += `

                        <p>

                            <b>
                                ${venue.name}
                            </b>

                            <br>

                            Capacity:
                            ${venue.capacity}

                            <br>

                            Estimated Cost:
                            ₹${venue.estimated_cost}

                        </p>

                    `;

                }
            );


        html += `

            </div>

        `;

    }


    html += `

        <div class="card">

            <h3>
                Suggestions
            </h3>

            <ul>

    `;


    (
        data.additional_suggestions ||
        []
    ).forEach(
        suggestion => {

            html += `
                <li>
                    ${suggestion}
                </li>
            `;

        }
    );


    html += `

            </ul>

        </div>

    `;


    html += `

        </div>

    `;


    $("result").innerHTML =
        html;

}


// ============================================================
// HISTORY
// ============================================================

async function loadHistory() {

    try {

        const data =
            await api(
                "/api/history"
            );


        const list =
            data.history;


        if (!list.length) {

            $("historyList").innerHTML =
                "<p>No recommendations yet.</p>";

            return;

        }


        let html = "";


        list.forEach(
            item => {

                html += `

                    <div class="card">

                        <h3>
                            ${item.kind}
                        </h3>

                        <p>
                            Budget:
                            ₹${Number(
                                item.total_budget
                            ).toLocaleString(
                                "en-IN"
                            )}
                        </p>

                        <p>
                            ${item.created_at}
                        </p>

                        <button
                            onclick="viewHistory('${item.id}')"
                        >
                            View
                        </button>

                    </div>

                `;

            }
        );


        $("historyList").innerHTML =
            html;

    }
    catch (error) {

        alert(
            error.message
        );

    }

}


// ============================================================
// HISTORY DETAIL
// ============================================================

async function viewHistory(id) {

    try {

        const data =
            await api(
                "/api/history/" + id
            );


        displayResult(
            data.result
        );


        window.scrollTo(
            0,
            document.body.scrollHeight
        );

    }
    catch (error) {

        alert(
            error.message
        );

    }

}


// ============================================================
// INITIALIZE
// ============================================================

async function initialize() {

    try {

        const user =
            await api(
                "/api/me"
            );


        $("welcome")
            .classList
            .add("hidden");


        $("application")
            .classList
            .remove("hidden");


        $("authStatus")
            .textContent =
            "Hello, " +
            (
                user.full_name ||
                user.username
            );

    }
    catch (error) {

        // User is not logged in.
    }

}


initialize();