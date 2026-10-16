/* Desenha os graficos de /relatorios (spec 05 §5) a partir do JSON embutido na pagina.
 *
 * Uma serie por grafico, uma cor (--serie-1, validada contra as duas superficies).
 * O tipo de grafico e escolha de apresentacao: cada <select data-grafico> troca so
 * entre os tipos que a spec lista. O dado nao muda — so o desenho.
 *
 * Dinheiro chega em CENTAVOS inteiros. A divisao por 100 abaixo e so para EXIBIR
 * (rotulo e tooltip); o valor plotado continua o inteiro, e a tabela gemea de cada
 * grafico mostra o numero exato, formatado no servidor.
 */
(function () {
  "use strict";

  var moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  // No eixo, sem centavos sobrando: "R$ 10" em vez de "R$ 10,00" — rotulo curto nao inclina.
  var moedaEixo = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  var instancias = {};

  function reais(centavos) {
    return moeda.format(centavos / 100);
  }

  function reaisEixo(centavos) {
    return moedaEixo.format(centavos / 100);
  }

  // Filiais de uma rede tem o MESMO nome e CNPJs diferentes; produto sem codigo de
  // barras e um por loja. Rotulo repetido ganha o fim do CNPJ, senao as barras se
  // confundem. Rotulo unico fica limpo.
  function desambiguar(rotulos, cnpjs) {
    var vezes = {};
    rotulos.forEach(function (r) {
      vezes[r] = (vezes[r] || 0) + 1;
    });
    return rotulos.map(function (r, i) {
      return vezes[r] > 1 && cnpjs[i] ? r + " · …" + cnpjs[i].slice(-6) : r;
    });
  }

  function ler(nome) {
    var elemento = document.getElementById("dados-" + nome);
    return elemento ? JSON.parse(elemento.textContent) : null;
  }

  function tema() {
    var css = getComputedStyle(document.documentElement);
    function v(nome) {
      return css.getPropertyValue(nome).trim();
    }
    return {
      serie: v("--serie-1"),
      neutra: v("--serie-neutra"),
      grade: v("--grade"),
      eixo: v("--eixo"),
      texto: v("--suave"),
    };
  }

  function dataBr(milissegundos) {
    return new Date(milissegundos).toLocaleDateString("pt-BR");
  }

  function curto(texto) {
    return texto.length > 28 ? texto.slice(0, 27) + "…" : texto;
  }

  // eixoValor: "x" ou "y" — qual eixo carrega o numero. O outro carrega os rotulos.
  // `formatar` serve o tooltip (exato); o eixo usa `formatarEixo` (curto), se dado.
  function opcoes(t, eixoValor, formatar, extra, formatarEixo) {
    var valor = {
      beginAtZero: true,
      grid: { color: t.grade },
      border: { color: t.eixo },
      ticks: { color: t.texto, callback: formatarEixo || formatar, maxRotation: 0, maxTicksLimit: 6 },
    };
    var rotulos = {
      grid: { display: false },
      border: { color: t.eixo },
      ticks: {
        color: t.texto,
        callback: function (indice) {
          return curto(String(this.getLabelForValue(indice)));
        },
      },
    };
    var base = {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false }, // uma serie so: o titulo do cartao a nomeia
        tooltip: {
          callbacks: {
            label: function (contexto) {
              return formatar(contexto.parsed[eixoValor]);
            },
          },
        },
      },
      scales: eixoValor === "x" ? { x: valor, y: rotulos } : { x: rotulos, y: valor },
    };
    return Object.assign(base, extra || {});
  }

  function barras(rotulos, valores, cores, horizontal, t) {
    return {
      type: "bar",
      data: {
        labels: rotulos,
        datasets: [
          {
            data: valores,
            backgroundColor: cores,
            borderRadius: 4,
            borderSkipped: "start", // arredonda so a ponta do dado, nunca a base
            maxBarThickness: 28,
          },
        ],
      },
      options: opcoes(t, horizontal ? "x" : "y", reais, { indexAxis: horizontal ? "y" : "x" }, reaisEixo),
    };
  }

  function serieDeUmaCor(t, valores) {
    return valores.map(function () {
      return t.serie;
    });
  }

  var desenhos = {
    mensal: function (tipo, t) {
      var d = ler("mensal");
      return {
        type: tipo,
        data: {
          labels: d.map(function (p) { return p.mes; }),
          datasets: [
            {
              data: d.map(function (p) { return p.gasto; }),
              borderColor: t.serie,
              backgroundColor: t.serie,
              borderWidth: 2,
              pointRadius: 4,
              pointHoverRadius: 6,
              borderRadius: 4,
              borderSkipped: "start",
              maxBarThickness: 28,
            },
          ],
        },
        options: opcoes(t, "y", reais, { interaction: { mode: "index", intersect: false } }, reaisEixo),
      };
    },

    categoria: function (orientacao, t) {
      var d = ler("categoria");
      var rotulos = d.linhas.map(function (l) { return l.nome; });
      var valores = d.linhas.map(function (l) { return l.gasto; });
      var cores = serieDeUmaCor(t, valores);
      // O nao classificado aparece, em cinza: esconder seria fingir que todo gasto tem categoria.
      if (d.nao_classificado.gasto > 0) {
        rotulos.push("Não classificado");
        valores.push(d.nao_classificado.gasto);
        cores.push(t.neutra);
      }
      return barras(rotulos, valores, cores, orientacao === "horizontal", t);
    },

    loja: function (orientacao, t) {
      var d = ler("loja");
      var valores = d.map(function (l) { return l.gasto; });
      return barras(
        desambiguar(
          d.map(function (l) { return l.emit_nome || l.emit_cnpj; }),
          d.map(function (l) { return l.emit_cnpj; })
        ),
        valores,
        serieDeUmaCor(t, valores),
        orientacao === "horizontal",
        t
      );
    },

    top: function (orientacao, t) {
      var d = ler("top");
      var valores = d.map(function (p) { return p.gasto; });
      return barras(
        desambiguar(
          d.map(function (p) { return p.descricao_exemplo; }),
          d.map(function (p) { return p.emit_cnpj; })
        ),
        valores,
        serieDeUmaCor(t, valores),
        orientacao === "horizontal",
        t
      );
    },

    preco: function (tipo, t) {
      var d = ler("preco");
      function precoUnitario(valor) {
        return moeda.format(valor);
      }
      var opcoesPreco = opcoes(t, "y", precoUnitario, {
        interaction: { mode: "nearest", intersect: false },
      });
      opcoesPreco.plugins.tooltip.callbacks.title = function (itens) {
        return dataBr(itens[0].parsed.x);
      };
      opcoesPreco.plugins.tooltip.callbacks.label = function (contexto) {
        var ponto = d.pontos[contexto.dataIndex];
        return precoUnitario(contexto.parsed.y) + " — " + (ponto.emit_nome || ponto.emit_cnpj);
      };
      // ⚠️ Eixo de TEMPO de verdade (numero = milissegundos), e nao de categorias: as
      // compras sao irregulares, e um eixo de categorias poria 20/05, 02/06 e 12/09 a
      // distancias iguais. O eixo "time" do Chart.js exigiria um adaptador de datas;
      // o linear com rotulo formatado da o mesmo espacamento sem dependencia nova.
      // O eixo vai da primeira a ultima compra; sozinho, o Chart.js arredondaria para
      // datas sem compra nenhuma. Um ponto so ganha um dia de folga de cada lado.
      var datas = d.pontos.map(function (p) { return Date.parse(p.data); });
      var folga = datas.length > 1 ? 0 : 86400000;
      opcoesPreco.scales.x = {
        type: "linear",
        min: Math.min.apply(null, datas) - folga,
        max: Math.max.apply(null, datas) + folga,
        grid: { display: false },
        border: { color: t.eixo },
        ticks: { color: t.texto, maxRotation: 0, maxTicksLimit: 5, callback: dataBr },
      };
      return {
        type: "line",
        data: {
          datasets: [
            {
              // A string decimal vira numero SO para posicionar o ponto; a tabela mostra a exata.
              data: d.pontos.map(function (p) {
                return { x: Date.parse(p.data), y: Number(p.valor_unitario) };
              }),
              borderColor: t.serie,
              backgroundColor: t.serie,
              borderWidth: 2,
              pointRadius: 4,
              pointHoverRadius: 6,
              showLine: tipo !== "scatter",
              clip: false, // com o eixo justo nas compras, o ponto da ponta nao pode ser cortado
            },
          ],
        },
        options: opcoesPreco,
      };
    },
  };

  function desenhar(nome) {
    var canvas = document.getElementById("grafico-" + nome);
    var seletor = document.querySelector('select[data-grafico="' + nome + '"]');
    if (!canvas || !seletor || !ler(nome)) {
      return;
    }
    if (instancias[nome]) {
      instancias[nome].destroy();
    }
    instancias[nome] = new Chart(canvas, desenhos[nome](seletor.value, tema()));
  }

  function desenharTodos() {
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Object.keys(desenhos).forEach(desenhar);
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (typeof Chart === "undefined") {
      return; // sem o Chart.js, as tabelas gemeas continuam com todos os numeros
    }
    document.querySelectorAll("select[data-grafico]").forEach(function (seletor) {
      seletor.addEventListener("change", function () {
        desenhar(seletor.dataset.grafico);
      });
    });
    desenharTodos();
    // O tema escuro tem cores proprias: troca de tema redesenha com elas.
    var escuro = window.matchMedia("(prefers-color-scheme: dark)");
    if (escuro.addEventListener) {
      escuro.addEventListener("change", desenharTodos);
    }
  });
})();
