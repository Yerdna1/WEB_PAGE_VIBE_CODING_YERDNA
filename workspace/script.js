const agent = document.getElementById('agent');
const goal = document.getElementById('goal');
const environment = document.getElementById('environment');

// Získanie rozmerov prostredia a cieľa
const envRect = environment.getBoundingClientRect();
const goalRect = goal.getBoundingClientRect();

// Pozícia agenta (aktuálna)
let agentX = agent.offsetLeft;
let agentY = agent.offsetTop;

// Pozícia cieľa (relatívne k prostrediu)
// Odpočítame pozíciu prostredia, aby sme získali relatívne súradnice
// A upravíme o polovicu rozmeru cieľa, aby sme mierili na stred
const goalX = goal.offsetLeft + goal.offsetWidth / 2 - agent.offsetWidth / 2;
const goalY = goal.offsetTop + goal.offsetHeight / 2 - agent.offsetHeight / 2;

// Rýchlosť agenta (pixelov za krok)
const speed = 2;
let animationFrameId = null;

function moveAgent() {
    // Vypočítať vektor smerom k cieľu
    const dx = goalX - agentX;
    const dy = goalY - agentY;

    // Vypočítať vzdialenosť k cieľu
    const distance = Math.sqrt(dx * dx + dy * dy);

    // Ak sme dostatočne blízko, zastaviť animáciu
    if (distance < speed) {
        agentX = goalX;
        agentY = goalY;
        agent.style.transform = `translate(${agentX - agent.offsetLeft}px, ${agentY - agent.offsetTop}px)`;
        console.log("Cieľ dosiahnutý!");
        cancelAnimationFrame(animationFrameId);
        // Prípadne zmeniť farbu agenta alebo cieľa
        agent.style.backgroundColor = '#f1c40f'; // Žltá po dosiahnutí
        return; // Ukončiť funkciu
    }

    // Normalizovať smerový vektor (aby mal dĺžku 1)
    const normDx = dx / distance;
    const normDy = dy / distance;

    // Posunúť agenta o krok v správnom smere
    agentX += normDx * speed;
    agentY += normDy * speed;

    // Jednoduchá kontrola hraníc prostredia
    agentX = Math.max(0, Math.min(envRect.width - agent.offsetWidth, agentX));
    agentY = Math.max(0, Math.min(envRect.height - agent.offsetHeight, agentY));

    // Aplikovať novú pozíciu cez transformáciu pre plynulejší pohyb
    // Potrebujeme posunúť relatívne k pôvodnej pozícii definovanej v CSS
    const translateX = agentX - agent.offsetLeft;
    const translateY = agentY - agent.offsetTop;
    agent.style.transform = `translate(${translateX}px, ${translateY}px)`;

    // Požiadať o ďalší krok animácie
    animationFrameId = requestAnimationFrame(moveAgent);
}

// Spustiť animáciu
animationFrameId = requestAnimationFrame(moveAgent);

console.log("Simulácia spustená. Agent hľadá cieľ.");
console.log(`Cieľ na pozícii (relatívne): X=${goalX.toFixed(2)}, Y=${goalY.toFixed(2)}`);