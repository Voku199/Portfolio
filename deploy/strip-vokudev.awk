# Vypíše Caddyfile bez bloku hlavního webu. Blok vyhodí jen tehdy, když jsou v hlavičce VÝHRADNĚ
# vokudev.cz a www.vokudev.cz, takže 9b.vokudev.cz a další subdomény zůstanou. Hlavičku, která hlavní
# web míchá s jinou adresou, nechá být: nový blok by s ní kolidoval a caddy validate to zastaví.

function jen_hlavni_web(hlava,    n, i, jmena, nalezeno) {
    sub(/\{[[:space:]]*$/, "", hlava)
    gsub(/,/, " ", hlava)
    n = split(hlava, jmena, " ")
    nalezeno = 0
    for (i = 1; i <= n; i++) {
        if (jmena[i] != "vokudev.cz" && jmena[i] != "www.vokudev.cz") return 0
        nalezeno = 1
    }
    return nalezeno
}

depth == 0 && /\{[[:space:]]*$/ && jen_hlavni_web($0) { skip = 1 }

{
    line = $0
    sub(/^[[:space:]]*#.*/, "", line)      # závorky v komentáři se nepočítají
    opens = gsub(/\{/, "{", line)
    closes = gsub(/\}/, "}", line)
    if (!skip) print
    depth += opens - closes
    if (skip && depth == 0) skip = 0
}
