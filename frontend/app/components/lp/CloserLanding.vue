<script setup lang="ts">
// LP de pré-qualificação SDR e Closer (Grupo Enriquecedor). Layout fixo, específico
// deste template (Course.lp_template === 'closer'). O <form> vem pelo slot #form.
defineProps<{ course: { id: number; name: string; image: string | null } }>()
</script>

<template>
  <div class="min-h-screen bg-[#080808] text-white">
    <!-- Banner de atenção -->
    <div class="bg-red-600 text-white">
      <p class="max-w-3xl mx-auto px-6 py-4 text-sm md:text-[15px] leading-relaxed text-center">
        <strong class="font-bold">Atenção!</strong> Todas as vagas,
        <strong class="font-bold">sem exceção</strong>, do Grupo Enriquecedor e de empresas
        pertencentes ao nosso ecossistema são
        <u class="font-semibold">vagas para <strong>dedicação exclusiva e tempo integral</strong></u>,
        seja atuando como Closer, SDR ou Social Seller. Desejamos e buscamos apenas pessoas que
        vão ter apenas um foco. Por isso, se não está de acordo com esse item, não prossiga no
        processo seletivo e, caso prossiga, temos diversas formas de identificar esse comportamento
        caso seja omitido durante o processo.
      </p>
    </div>

    <!-- Hero -->
    <section class="relative overflow-hidden">
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-red-900/25 via-[#080808] to-[#080808]" />
      <div class="relative max-w-3xl mx-auto px-6 pt-14 pb-10 text-center">
        <h1 class="font-black uppercase tracking-tighter leading-[0.95] text-4xl md:text-6xl">
          <span class="block text-[#265F34]">Pré-qualificação SDR e Closer</span>
          <span class="block text-white">Grupo Enriquecedor</span>
        </h1>

        <p class="mt-8 text-sm md:text-base text-white/70 leading-relaxed">
          Seja bem vindo e parabéns por ter chegado a etapa e pré-qualificação para ser um SDR ou
          Closer nas empresas assessoradas pela Grupo Enriquecedor e pertencentes ao nosso
          ecossistema de negócios!! O curso que você irá se cadastrar serão essenciais para sua atuação de sucesso na
          área, seja conosco ou com qualquer empresa que possa vir a te contratar para esta função.
          Tenha certeza que você terá um conteúdo de extremo valor e altamente especializado para
          seu desenvolvimento profissional. Para se qualificar para a próxima etapa, que é a
          entrevista final com o gestor da área, é necessário estudar o material com afinco e
          realizar o questionário sobre os materiais da forma mais completa possível. Te aguardamos
          na próxima fase! Bons estudos!
        </p>
      </div>
    </section>

    <!-- Form de cadastro (logo após a primeira dobra) -->
    <section class="px-6 pb-16">
      <div class="max-w-md mx-auto bg-white/5 border border-white/10 rounded-xl p-7 md:p-9 shadow-2xl">
        <slot name="form" />
      </div>
    </section>

    <!-- Por que estudar antes de ser contratado -->
    <section class="border-t border-white/5 bg-[#0a0a0a]">
      <div class="max-w-3xl mx-auto px-6 py-14">
        <h2 class="text-2xl md:text-3xl font-bold tracking-tight text-center mb-8">
          Por que estou estudando isso antes de ser contratado?
        </h2>

        <div class="space-y-5 text-sm md:text-[15px] leading-relaxed text-white/75">
          <p class="text-red-500 font-bold">
            Boa pergunta! Bom, existem 3 tipos de pessoas que reagem de formas diferentes a essa questão:
          </p>

          <p>
            <strong class="text-red-500 font-bold">Tipo de Pessoa 1</strong> - Vai bater o pé e que
            isso é um treinamento e que só vai ser treinado quando for contratado, até lá não deverá
            fazer nenhum esforço em se qualificar a não ser participar das entrevistas.
          </p>
          <p>
            <strong class="text-red-500 font-bold">Tipo de Pessoa 2</strong> - Em vez de estudar e
            se agregar com o material, vai querer "burlar" o processo e vai ir nas partes onde
            encontrará as respostas para as perguntas da aplicação. E isso não será difícil.
          </p>
          <p>
            <strong class="text-red-500 font-bold">Tipo de Pessoa 3</strong> - Vai ter uma parcela
            das pessoas que é sedenta por conhecimento e desenvolvimento da sua própria carreira, e
            entendeu isto como uma oportunidade a mais de se desenvolver além de entender os porquês
            implícitos desse pré-treinamento.
          </p>

          <p>Se você é o tipo de pessoa 1, fique em paz.</p>
          <p>
            Nós organizamos o melhor treinamento possível, sucinto, altamente especializado e direto
            para sua alta performance profissional da função, o qual você poderá utilizar para
            revolucionar seu resultado profissional.
          </p>
          <p>
            Se você entende que não pode fazer esse esforço de estudar esses 5 conteúdos durante essa
            semana, tudo bem, te convidamos a deixar o processo, ele não é para você e desejamos
            sorte nos outros.
          </p>
          <p>
            Se você é o tipo de pessoa 2, é possível que identifiquemos essa atitude facilmente
            durante a análise do seu questionário. Se ainda sim passar por essa fase, você ainda terá
            a última entrevista com o gestor, ele sabe ver quem fez com afinco para se desenvolver e
            quem não, inclusive poderá fazer perguntar a respeito de um dos pré-treinamentos se ficar
            na dúvida. Por isso sugiro poupar o seu tempo e nosso tempo, não vai valer a pena.
          </p>
          <p>
            Agora se você se enquadra no tipo de pessoa 3 e você topa estudar e se pré-qualificar
            através desses conteúdos mesmo que sem a garantia de ser contratado, você é um perfil que
            buscamos.
          </p>
          <p>
            E se você está nesse grupo, parabéns, você já está na frente das pessoas do grupo 1 e 2.
            Você tem uma característica de mentalidade favorável a essa atuação e muito buscada no
            mundo profissional.
          </p>
          <p>Desejamos boa sorte nos estudos e te esperamos para a próxima fase.</p>
          <p>
            E lembre-se: a Grupo Enriquecedor é uma empresa que está constantemente contratando e
            treinando talentos para os negócios de destaque que contam com a nossa assessoria. Se
            qualificando nessa etapa, mesmo que não consiga a vaga pretendida hoje, você ainda estará
            na frente do nosso processo seletivo para ser chamado(a) para outras oportunidades, as
            quais garantimos boas condições de trabalho, valorização profissional, condições de
            remuneração acima da média e oportunidades de crescimento.
          </p>
          <p>
            Se acha que vale o risco estudar um material de alta qualidade em vendas para se
            desenvolver e passar para próxima fase, contamos com seu afinco nos estudos e te
            esperamos ansiosamente para a próxima etapa!
          </p>
        </div>
      </div>
    </section>
  </div>
</template>
