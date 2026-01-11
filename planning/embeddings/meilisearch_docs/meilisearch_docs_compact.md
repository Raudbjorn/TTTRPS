# Meilisearch Documentation

*Aggregated from official Meilisearch documentation*

---

# Overview

## Documentation

## Overview

 
 Get an overview of Meilisearch features and philosophy.
 
 
 See how Meilisearch compares to alternatives.
 
 
 Use Meilisearch with your favorite language and framework.
 

## Use case demos

Take at look at example applications built with Meilisearch.

 
 Search through multiple Eloquent models with Laravel.
 
 
 Browse millions of products in our Nuxt 3 e-commerce demo app.
 
 
 Search across the TMDB movies databases using Next.js.

---

# Learning Resources

## Which embedder should I choose?

Meilisearch officially supports many different embedders, such as OpenAI, Hugging Face, and Ollama, as well as the majority of embedding generators with a RESTful API.

This article contains general guidance on how to choose the embedder best suited for your project.

## When in doubt, choose OpenAI

OpenAI returns relevant search results across different subjects and datasets. It is suited for the majority of applications and Meilisearch actively supports and improves OpenAI functionality with every new release.

In the majority of cases, and especially if this is your first time working with LLMs and AI-powered search, choose OpenAI.

## If you are already using a specific AI service, choose the REST embedder

If you are already using a specific model from a compatible embedder, choose Meilisearch's REST embedder. This ensures you continue building upon tooling and workflows already in place with minimal configuration necessary.

## If dealing with non-textual content, choose the user-provided embedder

Meilisearch does not support searching images, audio, or any other content not presented as text. This limitation applies to both queries and documents. e.g., Meilisearch's built-in embedder sources cannot search using an image instead of text. They also cannot use text to search for images without attached textual metadata.

In these cases, you will have to supply your own embeddings.

## Only choose Hugging Face when self-hosting small static datasets

Although it returns very relevant search results, the Hugging Face embedder must run directly in your server. This may lead to lower performance and extra costs when you are hosting Meilisearch in a service like DigitalOcean or AWS.

That said, Hugging Face can be a good embedder for datasets under 10k documents that you don't plan to update often.

Cloud does not support embedders with `{"source": "huggingFace"}`.

To implement Hugging Face embedders in the Cloud, use [HuggingFace inference points with the REST embedder](/guides/embedders/huggingface).

---

## Configure a REST embedder

You can integrate any text embedding generator with Meilisearch if your chosen provider offers a public REST API.

The process of integrating a REST embedder with Meilisearch varies depending on the provider and the way it structures its data. This guide shows you where to find the information you need, then walks you through configuring your Meilisearch embedder based on the information you found.

## Find your embedder provider's documentation

Each provider requires queries to follow a specific structure.

Before beginning to create your embedder, locate your provider's documentation for embedding creation. This should contain the information you need regarding API requests, request headers, and responses.

e.g., [Mistral's embeddings documentation](https://docs.mistral.ai/api/#tag/embeddings) is part of their API reference. In the case of [Cloudflare's Workers AI](https://developers.cloudflare.com/workers-ai/models/bge-base-en-v1.5/#Parameters), expected input and response are tied to your chosen model.

## Set up the REST source and URL

Open your text editor and create an embedder object. Give it a name and set its source to `"rest"`:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest"
 }
}
```

Next, configure the URL Meilisearch should use to contact the embedding provider:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL"
 }
}
```

Setting an embedder name, a `source`, and a `url` is mandatory for all REST embedders.

## Configure the data Meilisearch sends to the provider

Meilisearch's `request` field defines the structure of the input it will send to the provider. The way you must fill this field changes for each provider.

e.g., Mistral expects two mandatory parameters: `model` and `input`. It also accepts one optional parameter: `encoding_format`. Cloudflare instead only expects a single field, `text`.

### Choose a model

In many cases, your provider requires you to explicitly set which model you want to use to create your embeddings. e.g., in Mistral, `model` must be a string specifying a valid Mistral model.

Update your embedder object adding this field and its value:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME"
 }
 }
}
```

In Cloudflare's case, the model is part of the API route itself and doesn't need to be specified in your `request`.

### The embedding prompt

The prompt corresponds to the data that the provider will use to generate your document embeddings. Its specific name changes depending on the provider you chose. In Mistral, this is the `input` field. In Cloudflare, it's called `text`.

Most providers accept either a string or an array of strings. A single string will generate one request per document in your database:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME",
 "input": "{{text}}"
 }
 }
}
```

`{{text}}` indicates Meilisearch should replace the contents of a field with your document data, as indicated in the embedder's [`documentTemplate`](/reference/api/settings#documenttemplate).

An array of strings allows Meilisearch to send up to 10 documents in one request, reducing the number of API calls to the provider:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME",
 "input": [
 "{{text}}", 
 "{{..}}"
 ]
 }
 }
}
```

When using array prompts, the first item must be `{{text}}`. If you want to send multiple documents in a single request, the second array item must be `{{..}}`. When using `"{{..}}"`, it must be present in both `request` and `response`.

When using other embedding providers, `input` might be called something else, like `text` or `prompt`:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME",
 "text": "{{text}}"
 }
 }
}
```

### Provide other request fields

You may add as many fields to the `request` object as you need. Meilisearch will include them when querying the embeddings provider.

e.g., Mistral allows you to optionally configure an `encoding_format`. Set it by declaring this field in your embedder's `request`:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME",
 "input": ["{{text}}", "{{..}}"],
 "encoding_format": "float"
 }
 }
}
```

## The embedding response

You must indicate where Meilisearch can find the document embeddings in the provider's response. Consult your provider's API documentation, paying attention to where it places the embeddings.

Cloudflare's embeddings are located in an array inside `response.result.data`. Describe the full path to the embedding array in your embedder's `response`. The first array item must be `"{{embedding}}"`:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "text": "{{text}}"
 },
 "response": {
 "result": {
 "data": ["{{embedding}}"]
 }
 }
 }
}
```

If the response contains multiple embeddings, use `"{{..}}"` as its second value:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME",
 "input": [
 "{{text}}", 
 "{{..}}"
 ]
 },
 "response": {
 "data": [
 {
 "embedding": "{{embedding}}"
 },
 "{{..}}"
 ]
 }
 }
}
```

When using `"{{..}}"`, it must be present in both `request` and `response`.

It is possible the response contains a single embedding outside of an array. Use `"{{embedding}}"` as its value:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME",
 "input": "{{text}}"
 },
 "response": {
 "data": {
 "text": "{{embedding}}"
 }
 }
 }
}
```

It is also possible the response is a single item or array not nested in an object:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME",
 "input": [
 "{{text}}",
 "{{..}}"
 ]
 },
 "response": [
 "{{embedding}}",
 "{{..}}"
 ]
 }
}
```

The prompt data type does not necessarily match the response data type. e.g., Cloudflare always returns an array of embeddings, even if the prompt in your request was a string.

Meilisearch silently ignores `response` fields not pointing to an `"{{embedding}}"` value.

## The embedding header

Your provider might also request you to add specific headers to your request. e.g., Azure's AI services require an `api-key` header containing an API key.

Add the `headers` field to your embedder object:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "text": "{{text}}"
 },
 "response": {
 "result": {
 "data": ["{{embedding}}"]
 }
 },
 "headers": {
 "FIELD_NAME": "FIELD_VALUE"
 }
 }
}
```

By default, Meilisearch includes a `Content-Type` header. It may also include an authorization bearer token, if you have supplied an API key.

## Configure remainder of the embedder

`source`, `request`, `response`, and `header` are the only fields specific to REST embedders.

Like other remote embedders, you're likely required to supply an `apiKey`:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME",
 "input": ["{{text}}", "{{..}}"],
 "encoding_format": "float"
 },
 "response": {
 "data": [
 {
 "embedding": "{{embedding}}"
 },
 "{{..}}"
 ]
 },
 "apiKey": "PROVIDER_API_KEY",
 }
}
```

You should also set a `documentTemplate`. Good templates are short and include only highly relevant document data:

```json
{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME",
 "input": ["{{text}}", "{{..}}"],
 "encoding_format": "float"
 },
 "response": {
 "data": [
 {
 "embedding": "{{embedding}}"
 },
 "{{..}}"
 ]
 },
 "apiKey": "PROVIDER_API_KEY",
 "documentTemplate": "SHORT_AND_RELEVANT_DOCUMENT_TEMPLATE"
 }
}
```

## Update your index settings

Now the embedder object is complete, update your index settings:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/indexes/INDEX_NAME/settings/embedders' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "EMBEDDER_NAME": {
 "source": "rest",
 "url": "PROVIDER_URL",
 "request": {
 "model": "MODEL_NAME",
 "input": ["{{text}}", "{{..}}"],
 },
 "response": {
 "data": [
 {
 "embedding": "{{embedding}}"
 },
 "{{..}}"
 ]
 },
 "apiKey": "PROVIDER_API_KEY",
 "documentTemplate": "SHORT_AND_RELEVANT_DOCUMENT_TEMPLATE"
 }
 }'
```

## Conclusion

In this guide you have seen a few examples of how to configure a REST embedder in Meilisearch. Though it used Mistral and Cloudflare, the general steps remain the same for all providers:

1. Find the provider's REST API documentation
2. Identify the embedding creation request parameters
3. Include parameters in your embedder's `request`
4. Identify the embedding creation response
5. Reproduce the path to the returned embeddings in your embedder's `response`
6. Add any required HTTP headers to your embedder's `header`
7. Update your index settings with the new embedder

---

## Differences between full-text and AI-powered search

Meilisearch offers two types of search: full-text search and AI-powered search. This article explains their differences and intended use cases.

## Full-text search

This is Meilisearch's default search type. When performing a full-text search, Meilisearch checks the indexed documents for acceptable matches to a set of search terms. It is a fast and reliable search method.

e.g., when searching for `"pink sandals"`, full-text search will only return clothing items explicitly mentioning these two terms. Searching for `"pink summer shoes for girls"` is likely to return fewer and less relevant results.

## AI-powered search

AI-powered search is Meilisearch's newest search method. It returns results based on a query's meaning and context.

AI-powered search uses LLM providers such as OpenAI and Hugging Face to generate vector embeddings representing the meaning and context of both query terms and documents. It then compares these vectors to find semantically similar search results.

When using AI-powered search, Meilisearch returns both full-text and semantic results by default. This is also called hybrid search.

With AI-powered search, searching for `"pink sandals"` will be more efficient, but queries for `"cute pink summer shoes for girls"` will still return relevant results including light-colored open shoes.

## Use cases

Full-text search is a reliable choice that works well in most scenarios. It is fast, less resource-intensive, and requires no extra configuration. It is best suited for situations where you need precise matches to a query and your users are familiar with the relevant keywords.

AI-powered search combines the flexibility of semantic search with the performance of full-text search. Most searches, whether short and precise or long and vague, will return very relevant search results. In most cases, AI-powered search will offer your users the best search experience, but will require extra configuration. AI-powered search may also entail extra costs if you use a third-party service such as OpenAI to generate vector embeddings.

---

## Document template best practices

When using AI-powered search, Meilisearch generates prompts by filling in your embedder's `documentTemplate` with each document's data. The better your prompt is, the more relevant your search results.

This guide shows you what to do and what to avoid when writing a `documentTemplate`.

## Sample document

Take a look at this document from a database of movies:

```json
{
 "id": 2,
 "title": "Ariel",
 "overview": "Taisto Kasurinen is a Finnish coal miner whose father has just committed suicide and who is framed for a crime he did not commit. In jail, he starts to dream about leaving the country and starting a new life. He escapes from prison but things don't go as planned...",
 "genres": [
 "Drama",
 "Crime",
 "Comedy"
 ],
 "poster": "https://image.tmdb.org/t/p/w500/ojDg0PGvs6R9xYFodRct2kdI6wC.jpg",
 "release_date": 593395200
}
```

## Do not use the default `documentTemplate`

Use a custom `documentTemplate` value in your embedder configuration.

The default `documentTemplate` includes all searchable fields with non-`null` values. In most cases, this adds noise and more information than the embedder needs to provide relevant search results.

## Only include highly relevant information

Take a look at your document and identify the most relevant fields. A good `documentTemplate` for the sample document could be:

```
"A movie called {{doc.title}} about {{doc.overview}}"
```

In the sample document, `poster` and `id` contain data that has little semantic importance and can be safely excluded. The data in `genres` and `release_date` is very useful for filters, but say little about this specific film.

This leaves two relevant fields: `title` and `overview`.

## Keep prompts short

For the best results, keep prompts somewhere between 15 and 45 words:

```
"A movie called {{doc.title}} about {{doc.overview | truncatewords: 20}}"
```

In the sample document, the `overview` alone is 49 words. Use Liquid's [`truncate`](https://shopify.github.io/liquid/filters/truncate/) or [`truncatewords`](https://shopify.github.io/liquid/filters/truncatewords/) to shorten it.

Short prompts do not have enough information for the embedder to properly understand the query context. Long prompts instead provide too much information and make it hard for the embedder to identify what is truly relevant about a document.

## Add guards for missing fields

Some documents might not contain all the fields you expect. If your template directly references a missing field, Meilisearch will throw an error when indexing documents.

To prevent this, use Liquid’s `if` statements to add guards around fields:

```
{% if doc.title %}
A movie called {{ doc.title }}
{% endif %}
```

This ensures the template only tries to include data that already exists in a document. If a field is missing, the embedder still receives a valid and useful prompt without errors.

## Conclusion

In this article you saw the main steps to generating prompts that lead to relevant AI-powered search results:

- Do not use the default `documentTemplate`
- Only include relevant data
- Truncate long fields
- Add guards for missing fields

---

## Getting started with AI-powered search

[AI-powered search](https://meilisearch.com/solutions/vector-search), sometimes also called vector search or hybrid search, uses [large language models (LLMs)](https://en.wikipedia.org/wiki/Large_language_model) to retrieve search results based on the meaning and context of a query.

This tutorial will walk you through configuring AI-powered search in your Meilisearch project. You will see how to set up an embedder with OpenAI, generate document embeddings, and perform your first search.

## Requirements

- A running Meilisearch project
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A command-line console

## Create a new index

First, create a new Meilisearch project. If this is your first time using Meilisearch, follow the [quick start](/learn/getting_started/cloud_quick_start) then come back to this tutorial.

Next, create a `kitchenware` index and add [this kitchenware products dataset](/assets/datasets/kitchenware.json) to it. It will take Meilisearch a few moments to process your request, but you can continue to the next step while your data is indexing.

## Generate embeddings with OpenAI

In this step, you will configure an OpenAI embedder. Meilisearch uses **embedders** to translate documents into **embeddings**, which are mathematical representations of a document's meaning and context.

Open a blank file in your text editor. You will only use this file to build your embedder one step at a time, so there's no need to save it if you plan to finish the tutorial in one sitting.

### Choose an embedder name

In your blank file, create your `embedder` object:

```json
{
 "products-openai": {}
}
```

`products-openai` is the name of your embedder for this tutorial. You can name embedders any way you want, but try to keep it simple, short, and easy to remember.

### Choose an embedder source

Meilisearch relies on third-party services to generate embeddings. These services are often referred to as the embedder source.

Add a new `source` field to your embedder object:

```json
{
 "products-openai": {
 "source": "openAi"
 }
}
```

Meilisearch supports several embedder sources. This tutorial uses OpenAI because it is a good option that fits most use cases.

### Choose an embedder model

Models supply the information required for embedders to process your documents.

Add a new `model` field to your embedder object:

```json
{
 "products-openai": {
 "source": "openAi",
 "model": "text-embedding-3-small"
 }
}
```

Each embedder service supports different models targeting specific use cases. `text-embedding-3-small` is a cost-effective model for general usage.

### Create your API key

Log into OpenAI, or create an account if this is your first time using it. Generate a new API key using [OpenAI's web interface](https://platform.openai.com/api-keys).

Add the `apiKey` field to your embedder:

```json
{
 "products-openai": {
 "source": "openAi",
 "model": "text-embedding-3-small",
 "apiKey": "OPEN_AI_API_KEY",
 }
}
```

Replace `OPEN_AI_API_KEY` with your own API key.

You may use any key tier for this tutorial. Use at least [Tier 2 keys](https://platform.openai.com/docs/guides/rate-limits/usage-tiers?context=tier-two) in production environments.

### Design a prompt template

Meilisearch embedders only accept textual input, but documents can be complex objects containing different types of data. This means you must convert your documents into a single text field. Meilisearch uses [Liquid](https://shopify.github.io/liquid/basics/introduction/), an open-source templating language to help you do that.

A good template should be short and only include the most important information about a document. Add the following `documentTemplate` to your embedder:

```json
{
 "products-openai": {
 "source": "openAi",
 "model": "text-embedding-3-small",
 "apiKey": "OPEN_AI_API_KEY",
 "documentTemplate": "An object used in a kitchen named '{{doc.name}}'"
 }
}
```

This template starts by giving the general context of the document: `An object used in a kitchen`. Then it adds the information i.e. specific to each document: `doc` represents your document, and you can access any of its attributes using dot notation. `name` is an attribute with values such as `wooden spoon` or `rolling pin`. Since it is present in all documents in this dataset and describes the product in few words, it is a good choice to include in the template.

### Create the embedder

Your embedder object is ready. Send it to Meilisearch by updating your index settings:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/indexes/kitchenware/settings/embedders' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "products-openai": {
 "source": "openAi",
 "apiKey": "OPEN_AI_API_KEY",
 "model": "text-embedding-3-small",
 "documentTemplate": "An object used in a kitchen named '{{doc.name}}'"
 }
 }'
```

Replace `MEILISEARCH_URL` with the address of your Meilisearch project, and `OPEN_AI_API_KEY` with your [OpenAI API key](https://platform.openai.com/api-keys).

Meilisearch and OpenAI will start processing your documents and updating your index. This may take a few moments, but once it's done you are ready to perform an AI-powered search.

## Perform an AI-powered search

AI-powered searches are very similar to basic text searches. You must query the `/search` endpoint with a request containing both the `q` and the `hybrid` parameters:

```sh
curl \
 -X POST 'MEILISEARCH_URL/indexes/kitchenware/search' \
 -H 'content-type: application/json' \
 --data-binary '{
 "q": "kitchen utensils made of wood",
 "hybrid": {
 "embedder": "products-openai"
 }
 }'
```

For this tutorial, `hybrid` is an object with a single `embedder` field.

Meilisearch will then return an equal mix of semantic and full-text matches.

## Conclusion

Congratulations! You have created an index, added a small dataset to it, and activated AI-powered search. You then used OpenAI to generate embeddings out of your documents, and performed your first AI-powered search.

## Next steps

Now you have a basic overview of the basic steps required for setting up and performing AI-powered searches, you might want to try and implement this feature in your own application.

For practical information on implementing AI-powered search with other services, consult our [guides section](/guides/embedders/openai). There you will find specific instructions for embedders such as [LangChain](/guides/langchain) and [Cloudflare](/guides/embedders/cloudflare).

For more in-depth information, consult the API reference for [embedder settings](/reference/api/settings#embedders) and [the `hybrid` search parameter](/reference/api/search#hybrid-search).

---

## Image search with multimodal embeddings

This guide shows the main steps to search through a database of images using Meilisearch's experimental multimodal embeddings.

## Requirements

- A database of images
- A Meilisearch project 
- Access to a multimodal embedding provider (e.g., [VoyageAI multimodal embeddings](https://docs.voyageai.com/reference/multimodal-embeddings-api)) 

## Enable multimodal embeddings

First, enable the `multimodal` experimental feature:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "multimodal": true
 }'
```

You may also enable multimodal in your Cloud project's general settings, under "Experimental features".

## Configure a multimodal embedder

Much like other embedders, multimodal embedders must set their `source` to `rest` and explicitly declare their `url`. Depending on your chosen provider, you may also have to specify `apiKey`.

All multimodal embedders must contain an `indexingFragments` field and a `searchFragments` field. Fragments are sets of embeddings built out of specific parts of document data.

Fragments must follow the structure defined by the REST API of your chosen provider.

### `indexingFragments`

Use `indexingFragments` to tell Meilisearch how to send document data to the provider's API when generating document embeddings.

e.g., when using VoyageAI's multimodal model, an indexing fragment might look like this:

```json
"indexingFragments": {
 "TEXTUAL_FRAGMENT_NAME": {
 "value": {
 "content": [
 {
 "type": "text",
 "text": "A document named {{doc.title}} described as {{doc.description}}"
 }
 ]
 }
 },
 "IMAGE_FRAGMENT_NAME": {
 "value": {
 "content": [
 {
 "type": "image_url",
 "image_url": "{{doc.poster_url}}"
 }
 ]
 }
 }
}
```

The example above requests Meilisearch to create two sets of embeddings during indexing: one for the textual description of an image, and another for the actual image.

Any JSON string value appearing in a fragment is handled as a Liquid template, where you interpolate document data present in `doc`. In `IMAGE_FRAGMENT_NAME`, that's `image_url` which outputs the plain URL string in the document field `poster_url`. In `TEXT_FRAGMENT_NAME`, `text` contains a longer string contextualizing two document fields, `title` and `description`.

### `searchFragments`

Use `searchFragments` to tell Meilisearch how to send search query data to the chosen provider's REST API when converting them into embeddings:

```json
"searchFragments": {
 "USER_TEXT_FRAGMENT": {
 "value": {
 "content": [
 {
 "type": "text",
 "text": "{{q}}"
 }
 ]
 }
 },
 "USER_SUBMITTED_IMAGE_FRAGMENT": {
 "value": {
 "content": [
 {
 "type": "image_base64",
 "image_base64": "data:{{media.image.mime}};base64,{{media.image.data}}"
 }
 ]
 }
 }
}
```

In this example, two modes of search are configured:

1. A textual search based on the `q` parameter, which will be embedded as text
2. An image search based on [data url](https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/data) rebuilt from the `image.mime` and `image.data` field in the `media` field of the query

Search fragments have access to data present in the query parameters `media` and `q`.

Each semantic search query for this embedder should match exactly one search fragment of this embedder, so the fragments should each have at least one disambiguating field

### Complete embedder configuration

Your embedder should look similar to this example with all fragments and embedding provider data:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/indexes/INDEX_NAME/settings' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "embedders": {
 "MULTIMODAL_EMBEDDER_NAME": {
 "source": "rest",
 "url": "https://api.voyageai.com/v1/multimodal-embeddings",
 "apiKey": "VOYAGE_API_KEY",
 "indexingFragments": {
 "TEXTUAL_FRAGMENT_NAME": {
 "value": {
 "content": [
 {
 "type": "text",
 "text": "A document named {{doc.title}} described as {{doc.description}}"
 }
 ]
 }
 },
 "IMAGE_FRAGMENT_NAME": {
 "value": {
 "content": [
 {
 "type": "image_url",
 "image_url": "{{doc.poster_url}}"
 }
 ]
 }
 }
 },
 "searchFragments": {
 "USER_TEXT_FRAGMENT": {
 "value": {
 "content": [
 {
 "type": "text",
 "text": "{{q}}"
 }
 ]
 }
 },
 "USER_SUBMITTED_IMAGE_FRAGMENT": {
 "value": {
 "content": [
 {
 "type": "image_base64",
 "image_base64": "data:{{media.image.mime}};base64,{{media.image.data}}"
 }
 ]
 }
 }
 },
 "request": {
 "inputs": [
 "{{fragment}}",
 "{{..}}"
 ],
 "model": "voyage-multimodal-3"
 },
 "response": {
 "data": [
 {
 "embedding": "{{embedding}}"
 },
 "{{..}}"
 ]
 }
 }
 }
 }'
```

Since the `source` of this embedder is `rest`, you must also specify a [`request` and a `response` fields](/reference/api/settings#body-21). These respectively instruct Meilisearch on how to structure the request sent to the embeddings provider, and where to find the embeddings in the provider's response.

## Add documents

Once your embedder is configured, you can [add documents to your index](/learn/getting_started/cloud_quick_start) with the [`/documents` endpoint](/reference/api/documents).

During indexing, Meilisearch will automatically generate multimodal embeddings for each document using the configured `indexingFragments`.

## Perform searches

The final step is to perform searches using different types of content.

### Use text to search for images

Use the following search query to retrieve a mix of documents with images matching the description, documents with and documents containing the specified keywords:

```sh
curl -X POST 'http://localhost:7700/indexes/INDEX_NAME/search' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "q": "a mountain sunset with snow",
 "hybrid": {
 "embedder": "MULTIMODAL_EMBEDDER_NAME"
 }
 }'
```

### Use an image to search for images

You can also use an image to search for other, similar images:

```sh
curl -X POST 'http://localhost:7700/indexes/INDEX_NAME/search' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "media": {
 "image": {
 "mime": "image/jpeg",
 "data": "<BASE64_ENCODED_IMAGE>"
 }
 },
 "hybrid": {
 "embedder": "MULTIMODAL_EMBEDDER_NAME"
 }
 }'
```

In most cases you will need a GUI interface that allows users to submit their images and converts these images to Base64 format. Creating this is outside the scope of this guide.

## Conclusion

With multimodal embedders you can:

1. Configure Meilisearch to embed both images and queries 
2. Add image documents — Meilisearch automatically generates embeddings 
3. Accept text or image input from users 
4. Run hybrid searches using a mix of textual and input from other types of media, or run pure semantic semantic searches using only non-textual input

---

## Image search with user-provided embeddings

This article shows you the main steps for performing multimodal searches where you can use text to search through a database of images with no associated metadata.

## Requirements

- A database of images
- A Meilisearch project
- An embedding generation provider you can install locally

## Configure your local embedding generation pipeline

First, set up a system that sends your images to your chosen embedding generation provider, then integrates the returned embeddings into your dataset.

The exact procedure depends heavily on your specific setup, but should include these main steps:

1. Choose a provider you can run locally
2. Choose a model that supports both image and text input
3. Send your images to the embedding generation provider
4. Add the returned embeddings to the `_vector` field for each image in your database

In most cases your system should run these steps periodically or whenever you update your database.

## Configure a user-provided embedder

Configure the `embedder` index setting, settings its source to `userProvided`:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/indexes/movies/settings' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "embedders": {
 "EMBEDDER_NAME": {
 "source": "userProvided",
 "dimensions": MODEL_DIMENSIONS
 }
 }
 }'
```

Replace `EMBEDDER_NAME` with the name you wish to give your embedder. Replace `MODEL_DIMENSIONS` with the number of dimensions of your chosen model.

## Add documents to Meilisearch Next, use [the `/documents` endpoint](/reference/api/documents) to upload the vectorized images.

In most cases, you should automate this step so Meilisearch is up to date with your primary database.

## Set up pipeline for vectorizing queries

Since you are using a `userProvided` embedder, you must also generate the embeddings for the search query. This process should be similar to generating embeddings for your images:

1. Receive user query from your front-end
2. Send query to your local embedding generation provider
3. Perform search using the returned query embedding

## Vector search with user-provided embeddings

Once you have the query's vector, pass it to the `vector` search parameter to perform a semantic AI-powered search:

```sh
curl -X POST -H 'content-type: application/json' \
 'localhost:7700/indexes/products/search' \
 --data-binary '{ 
 "vector": VECTORIZED_QUERY,
 "hybrid": {
 "embedder": "EMBEDDER_NAME",
 }
 }'
```

Replace `VECTORIZED_QUERY` with the embedding generated by your provider and `EMBEDDER_NAME` with your embedder.

If your images have any associated metadata, you may perform a hybrid search by including the original `q`:

```sh
curl -X POST -H 'content-type: application/json' \
 'localhost:7700/indexes/products/search' \
 --data-binary '{ 
 "vector": VECTORIZED_QUERY,
 "hybrid": {
 "embedder": "EMBEDDER_NAME",
 }
 "q": "QUERY",
 }'
```

## Conclusion

You have seen the main steps for implementing image search with Meilisearch:

1. Prepare a pipeline that converts your images into vectors
2. Index the vectorized images with Meilisearch 3. Prepare a pipeline that converts your users' queries into vectors
4. Perform searches using the converted queries

---

## Retrieve related search results

# Retrieve related search results

This guide shows you how to use the [similar documents endpoint](/reference/api/similar) to create an AI-powered movie recommendation workflow.

First, you will create an embedder and add documents to your index. You will then perform a search, and use the top result's primary key to retrieve similar movies in your database.

## Prerequisites

- A running Meilisearch project
- A [tier >=2](https://platform.openai.com/docs/guides/rate-limits#usage-tiers) OpenAI API key 

## Create a new index

Create an index called `movies` and add this <a href="/assets/datasets/movies.json" download="movies.json">`movies.json`</a> dataset to it. If necessary, consult the [getting started](/learn/getting_started/cloud_quick_start) for more instructions on index creation.

Each document in the dataset represents a single movie and has the following structure:

- `id`: a unique identifier for each document in the database
- `title`: the title of the movie
- `overview`: a brief summary of the movie's plot
- `genres`: an array of genres associated with the movie
- `poster`: a URL to the movie's poster image
- `release_date`: the release date of the movie, represented as a Unix timestamp

## Configure an embedder

Next, use the Cloud UI to configure an OpenAI embedder:

![Animated image of the Cloud UI showing a user clicking on "add embedder". This opens up a modal window, where the user fills in the name of the embedder, chooses OpenAI as its source. They then select a model, input their API key, and type out a document template.](/assets/images/similar-guide/01-add-embedder-ui.gif)

You may also use the `/settings/embedders` API subroute to configure your embedder:

Replace `MEILISEARCH_URL`, `MEILISEARCH_API_KEY`, and `OPENAI_API_KEY` with the corresponding values in your application.

Meilisearch will start generating the embeddings for all movies in your dataset. Use the returned `taskUid` to [track the progress of this task](/learn/async/asynchronous_operations). Once it is finished, you are ready to start searching.

## Perform a hybrid search

With your documents added and all embeddings generated, you can perform a search:

This request returns a list of movies. Pick the top result and take note of its primary key in the `id` field. In this case, it's the movie "Batman" with `id` 192.

## Return similar documents

Pass "Batman"'s `id` to your index's [`/similar` route](/reference/api/similar), specifying `movies-text` as your embedder:

Meilisearch will return a list of the 20 documents most similar to the movie you chose. You may then choose to display some of these similar results to your users, pointing them to other movies that may also interest them.

## Conclusion

Congratulations! You have successfully built an AI-powered movie search and recommendation system using Meilisearch by:

- Setting up a Meilisearch project and configured it for AI-powered search
- Implementing hybrid search combining keyword and semantic search capabilities
- Integrating Meilisearch's similarity search for movie recommendations

In a real-life application, you would now start integrating this workflow into a front end, like the one in this [official Meilisearch blog post](https://www.meilisearch.com/blog/add-ai-powered-search-to-react).

---

## Use AI-powered search with user-provided embeddings

This guide shows how to perform AI-powered searches with user-generated embeddings instead of relying on a third-party tool.

## Requirements

- A Meilisearch project

## Configure a custom embedder

Configure the `embedder` index setting, settings its source to `userProvided`:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/indexes/movies/settings' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "embedders": {
 "image2text": {
 "source": "userProvided",
 "dimensions": 3
 }
 }
 }'
```

Embedders with `source: userProvided` are incompatible with `documentTemplate` and `documentTemplateMaxBytes`.

## Add documents to Meilisearch Next, use [the `/documents` endpoint](/reference/api/documents?utm_campaign=vector-search&utm_source=docs&utm_medium=vector-search-guide) to upload vectorized documents. Place vector data in your documents' `_vectors` field:

```sh
curl -X POST -H 'content-type: application/json' \
'localhost:7700/indexes/products/documents' \
--data-binary '[
 { "id": 0, "_vectors": {"image2text": [0, 0.8, -0.2]}, "text": "frying pan" },
 { "id": 1, "_vectors": {"image2text": [1, -0.2, 0]}, "text": "baking dish" }
]'
```

## Vector search with user-provided embeddings

When using a custom embedder, you must vectorize both your documents and user queries.

Once you have the query's vector, pass it to the `vector` search parameter to perform an AI-powered search:

```sh
curl -X POST -H 'content-type: application/json' \
 'localhost:7700/indexes/products/search' \
 --data-binary '{ 
 "vector": [0, 1, 2],
 "hybrid": {
 "embedder": "image2text"
 }
 }'
```

`vector` must be an array of numbers indicating the search vector. You must generate these yourself when using vector search with user-provided embeddings.

`vector` can be used together with [other search parameters](/reference/api/search?utm_campaign=vector-search&utm_source=docs&utm_medium=vector-search-guide), including [`filter`](/reference/api/search#filter) and [`sort`](/reference/api/search#sort):

```sh
curl -X POST -H 'content-type: application/json' \
 'localhost:7700/indexes/products/search' \
 --data-binary '{
 "vector": [0, 1, 2],
 "filter": "price < 10",
 "sort": ["price:asc"],
 "hybrid": {
 "embedder": "image2text"
 }
 }'
```

---

## Analytics metrics reference

## Total searches

Total number of searches made during the specified period. Multi-search and federated search requests count as a single search.

## Total users

Total number of users who performed a search in the specified period.

Include the [user ID](/learn/analytics/bind_events_user) in your search request headers for the most accurate metrics. If search requests do not provide any user ID, the total amount of unique users will increase, as each request is assigned to a unique user ID.

## No result rate

Percentage of searches that did not return any results.

## Click-through rate

The ratio between the number of times users clicked on a result and the number of times Meilisearch showed that result. Since users will click on results that potentially match what they were looking for, a higher number indicates better relevancy.

Meilisearch does not have access to this information by default. You must [configure your application to submit click events](/learn/analytics/configure_analytics_events) to Meilisearch if you want to track it in the Cloud interface.

## Average click position

The average list position of clicked search results. A lower number means users have clicked on the first search results and indicates good relevancy.

Meilisearch does not have access to this information by default. You must [configure your application to submit click events](/learn/analytics/configure_analytics_events) to Meilisearch if you want to track it in the Cloud interface.

## Conversion

The percentage of searches resulting in a conversion event in your application. Conversion events vary depending on your application and indicate a user has performed a specific desired action. e.g., a conversion for an e-commerce website might mean a user has bought a product.

You must explicitly [configure your application to send conversion](/learn/analytics/configure_analytics_events) events when conditions are met.

It is not possible to associate multiple `conversion` events with the same query.

## Search requests

Total number of search requests within the specified time period.

## Search latency

The amount of time between a user making a search request and Cloud returning search results. A lower number indicates users receive search results more quickly.

## Most searched queries

Most common query terms users have used while searching.

## Searches without results

Most common query terms that did not return any search results.

## Countries with most searches

List of countries that generate the largest amount of search requests.

---

## Bind search analytics events to a user

import CodeSamplesAnalyticsEventBindSearch1 from '/snippets/samples/code_samples_analytics_event_bind_search_1.mdx';
import CodeSamplesAnalyticsEventBindEvent1 from '/snippets/samples/code_samples_analytics_event_bind_event_1.mdx';

This article refers to a new version of the Cloud analytics i.e. being rolled out in November 2025. Some features described here may not yet be available to your account. Contact support for more information.

## Requirements

- A Cloud project
- A method for identifying users
- A pipeline for submitting analytics events

## Assign user IDs to search requests

You can assign user IDs to search requests by including an `X-MS-USER-ID` header with your query:

Replace `SEARCH_USER_ID` with any value that uniquely identifies that user. This may be an authenticated user's ID when running searches from your own back end, or a hash of the user's IP address.

Assigning user IDs to search requests is optional. If a Cloud search request does not have an ID, Meilisearch will automatically generate one.

## Assign user IDs to analytics events

You can assign a user ID to analytics `/events` in two ways: HTTP headers or including it in the event payload.

If using HTTP headers, include an `X-MS-USER-ID` header with your query:

If you prefer to the event in your payload, include a `userId` field with your request:

Replace `SEARCH_USER_ID` with any value that uniquely identifies that user. This may be an authenticated user's ID when running searches from your own back end, or a hash of the user's IP address.

It is mandatory to specify a user ID when sending analytics events.

## Conclusion

In this guide you have seen how to bind analytics events to specific users by specifying an HTTP header for the search request, and either an HTTP header or a `userId` field for the analytics event.

---

## Configure Cloud analytics events

import CodeSamplesAnalyticsEventConversion1 from '/snippets/samples/code_samples_analytics_event_conversion_1.mdx';
import CodeSamplesAnalyticsEventClick1 from '/snippets/samples/code_samples_analytics_event_click_1.mdx';

This article refers to a new version of the Cloud analytics i.e. being rolled out in November 2025. Some features described here may not yet be available to your account. Contact support for more information.

## Requirements

You must have a [Cloud](https://meilisearch.com/cloud) account to access search analytics.

## Configure click-through rate and average click position

To track click-through rate and average click position, Cloud needs to know when users click on search results.

Every time a user clicks on a search result, your application must send a `click` event to the POST endpoint of Cloud's `/events` route:

You must explicitly submit a `userId` associated with the event. This can be any arbitrary string you use to identify the user, such as their profile ID in your application or their hashed IP address. You may submit user IDs directly on the event payload, or setting a `X-MS-USER-ID` request header.

Specifying a `queryUid` is optional but recommended as it ensures Meilisearch correctly associates the search query with the event. You can find the query UID in the [`metadata` field present in Cloud's search query responses](/reference/api/overview#search-metadata).

For more information, consult the [analytics events endpoint reference](/learn/analytics/events_endpoint).

## Configure conversion rate

To track conversion rate, first identify what should count as a conversion for your application. e.g., in a web shop a conversion might be a user finalizing the checkout process.

Once you have established what is a conversion in your application, configure it to send a `conversion` event to the POST endpoint of Cloud analytics route:

You must explicitly submit a `userId` associated with the event. This can be any arbitrary string you can use to identify the user, such as their profile ID in your application or their hashed IP address. You may submit user IDs directly on the event payload, or setting a `X-MS-USER-ID` request header.

Specifying a `queryUid` is optional but recommended as it ensures Meilisearch correctly associates the search query with the event. You can find the query UID in the `metadata` field present in Cloud's search query response.

It is not possible to associate multiple `conversion` events with the same query.

For more information, consult the [analytics events endpoint reference](/learn/analytics/events_endpoint).

---

## Analytics events endpoint

import CodeSamplesAnalyticsEventClick1 from '/snippets/samples/code_samples_analytics_event_click_1.mdx';

This article refers to a new version of the Cloud analytics i.e. being rolled out in November 2025. Some features described here may not yet be available to your account. Contact support for more information.

## Send an event

Send an analytics event to Cloud.

### Body | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | `eventType` | String | N/A | The event type, such as `click` or `conversion`, required | | `eventName` | String | N/A | A string describing the event, required | | `indexUid` | String | N/A | The name of the index of the clicked document, required | | `queryUid` | String | N/A | The [search query's UID](/reference/api/overview#search-metadata) | | `objectId` | String | N/A | The clicked document's primary key value | | `objectName` | String | N/A | A string describing the document | | `position` | Integer | N/A | An integer indicating the clicked document's position in the search result list | | `userId` | String | N/A | An arbitrary string identifying the user who performed the action | ```json
{
 "eventType": "click",
 "eventName": "Search Result Clicked",
 "indexUid": "products",
 "objectId": "0",
 "position": 0
}
```

You must provide a string identifying your user if you want Cloud to track conversion and click events.

You may do that in two ways:

- Specify the user ID in the payload, using the `userId` field
- Specify the user ID with the `X-MS-USER-ID` header with your `/events` and search requests

#### Example

##### Response: `201 Created`

---

## Migrate to the November 2025 Cloud analytics

This article refers to a new version of the Cloud analytics i.e. being rolled out in November 2025. Some features described here may not yet be available to your account. Contact support for more information.

## Analytics and monitoring are always active

Analytics and monitoring are now active in all Cloud projects. Basic functionality requires no extra configuration. Tracking user conversion, clickthrough, and clicked result position must instead be explicitly configured.

## Update URLs in your application

Meilisearch no longer requires `edge.meilisearch.com` to track search analytics. Update your application so all API requests, including click and conversion events, point to your project URL:

```sh
curl \
 -X POST 'https://PROJECT_URL/indexes/products/search' \
 -H 'Content-Type: application/json' \
 --data-binary '{ "q": "green socks" }'
```

`edge.meilisearch.com` remains functional, but no longer provides any benefit and will be discontinued in the future. If you created any custom API keys using the previous URL, you will also need to replace them.

---

## Tasks and asynchronous operations

Many operations in Meilisearch are processed **asynchronously**. These API requests are not handled immediately—instead, Meilisearch places them in a queue and processes them in the order they were received.

## Which operations are asynchronous?

Every operation that might take a long time to be processed is handled asynchronously. Processing operations asynchronously allows Meilisearch to handle resource-intensive tasks without impacting search performance.

Currently, these are Meilisearch's asynchronous operations:

- Creating an index
- Updating an index
- Swapping indexes
- Deleting an index
- Updating index settings
- Adding documents to an index
- Updating documents in an index
- Deleting documents from an index
- Canceling a task
- Deleting a task
- Creating a dump
- Creating snapshots

## Understanding tasks

When an API request triggers an asynchronous process, Meilisearch creates a task and places it in a [task queue](#task-queue).

### Task objects

Tasks are objects containing information that allow you to track their progress and troubleshoot problems when things go wrong.

A [task object](/reference/api/tasks#task-object) includes data not present in the original request, such as when the request was enqueued, the type of request, and an error code when the task fails:

```json
{
 "uid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 67493,
 "indexedDocuments": null
 },
 "error": null,
 "duration": null,
 "enqueuedAt": "2021-08-10T14:29:17.000000Z",
 "startedAt": null,
 "finishedAt": null
}
```

For a comprehensive description of each task object field, consult the [task API reference](/reference/api/tasks).

#### Summarized task objects

When you make an API request for an asynchronous operation, Meilisearch returns a [summarized version](/reference/api/tasks#summarized-task-object) of the full `task` object.

```json
{
 "taskUid": 0,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "indexCreation",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

Use the summarized task's `taskUid` to [track the progress of a task](/reference/api/tasks#get-one-task).

#### Task `status`

Tasks always contain a field indicating the task's current `status`. This field has one of the following possible values:

- **`enqueued`**: the task has been received and will be processed soon
- **`processing`**: the task is being processed
- **`succeeded`**: the task has been successfully processed
- **`failed`**: a failure occurred when processing the task. No changes were made to the database
- **`canceled`**: the task was canceled

`succeeded`, `failed`, and `canceled` tasks are finished tasks. Meilisearch keeps them in the task database but has finished processing these tasks. It is possible to [configure a webhook](/reference/api/webhooks) to notify external services when a task is finished.

`enqueued` and `processing` tasks are unfinished tasks. Meilisearch is either processing them or will do so in the future.

#### Global tasks

Some task types are not associated with a particular index but apply to the entire instance. These tasks are called global tasks. Global tasks always display `null` for the `indexUid` field.

Meilisearch considers the following task types as global:

- [`dumpCreation`](/reference/api/tasks#dumpcreation)
- [`taskCancelation`](/reference/api/tasks#taskcancelation)
- [`taskDeletion`](/reference/api/tasks#taskdeletion)
- [`indexSwap`](/reference/api/tasks#indexswap)
- [`snapshotCreation`](/reference/api/tasks#snapshotcreation)

In a protected instance, your API key must have access to all indexes (`"indexes": [*]`) to view global tasks.

### Task queue

After creating a task, Meilisearch places it in a queue. Enqueued tasks are processed one at a time, following the order in which they were requested.

When the task queue reaches its limit (about 10GiB), it will throw a `no_space_left_on_device` error. Users will need to delete tasks using the [delete tasks endpoint](/reference/api/tasks#delete-tasks) to continue write operations.

#### Task queue priority

Meilisearch considers certain tasks high-priority and always places them at the front of the queue.

The following types of tasks are always processed as soon as possible in this order:

1. `taskCancelation`
2. `upgradeDatabase`
3. `taskDeletion`
4. `indexCompaction`
5. `export`
6. `snapshotCreation`
7. `dumpCreation`

All other tasks are processed in the order they were enqueued.

## Task workflow

When you make a [request for an asynchronous operation](#which-operations-are-asynchronous), Meilisearch processes all tasks following the same steps:

1. Meilisearch creates a task, puts it in the task queue, and returns a [summarized `task` object](/learn/async/asynchronous_operations#summarized-task-objects). Task `status` set to `enqueued`
2. When your task reaches the front of the queue, Meilisearch begins working on it. Task `status` set to `processing`
3. Meilisearch finishes the task. Status set to `succeeded` if task was successfully processed, or `failed` if there was an error

**Terminating a Meilisearch instance in the middle of an asynchronous operation is completely safe** and will never adversely affect the database.

### Task batches

Meilisearch processes tasks in batches, grouping tasks for the best possible performance. In most cases, batching should be transparent and have no impact on the overall task workflow. Use [the `/batches` route](/reference/api/batches) to obtain more information on batches and how they are processing your tasks.

### Canceling tasks

You can cancel a task while it is `enqueued` or `processing` by using [the cancel tasks endpoint](/reference/api/tasks#cancel-tasks). Doing so changes a task's `status` to `canceled`.

Tasks are not canceled when you terminate a Meilisearch instance. Meilisearch discards all progress made on `processing` tasks and resets them to `enqueued`. Task handling proceeds as normal once the instance is relaunched.

### Deleting tasks

[Finished tasks](#task-status) remain visible in [the task list](/reference/api/tasks#get-tasks). To delete them manually, use the [delete tasks route](/reference/api/tasks#delete-tasks).

Meilisearch stores up to 1M tasks in the task database. If enqueuing a new task would exceed this limit, Meilisearch automatically tries to delete the oldest 100K finished tasks. If there are no finished tasks in the database, Meilisearch does not delete anything and enqueues the new task as usual.

#### Examples

Suppose you add a new document to your instance using the [add documents endpoint](/reference/api/documents#add-or-replace-documents) and receive a `taskUid` in response.

When you query the [get task endpoint](/reference/api/tasks#get-one-task) using this value, you see that it has been `enqueued`:

```json
{
 "uid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 67493,
 "indexedDocuments": null
 },
 "error": null,
 "duration": null,
 "enqueuedAt": "2021-08-10T14:29:17.000000Z",
 "startedAt": null,
 "finishedAt": null
}
```

Later, you check the task's progress one more time. It was successfully processed and its `status` changed to `succeeded`:

```json
{
 "uid": 1,
 "indexUid": "movies",
 "status": "succeeded",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 67493,
 "indexedDocuments": 67493
 },
 "error": null,
 "duration": "PT1S",
 "enqueuedAt": "2021-08-10T14:29:17.000000Z",
 "startedAt": "2021-08-10T14:29:18.000000Z",
 "finishedAt": "2021-08-10T14:29:19.000000Z"
}
```

Had the task failed, the response would have included a detailed `error` object:

```json
{
 "uid": 1,
 "indexUid": "movies",
 "status": "failed",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 67493,
 "indexedDocuments": 0
 },
 "error": {
 "message": "Document does not have a `:primaryKey` attribute: `:documentRepresentation`.",
 "code": "internal",
 "type": "missing_document_id",
 "link": "https://docs.meilisearch.com/errors#missing-document-id"
 },
 "duration": "PT1S",
 "enqueuedAt": "2021-08-10T14:29:17.000000Z",
 "startedAt": "2021-08-10T14:29:18.000000Z",
 "finishedAt": "2021-08-10T14:29:19.000000Z"
}
```

If the task had been [canceled](/reference/api/tasks#cancel-tasks) while it was `enqueued` or `processing`, it would have the `canceled` status and a non-`null` value for the `canceledBy` field.

After a task has been [deleted](/reference/api/tasks#delete-tasks), trying to access it returns a [`task_not_found`](/reference/errors/error_codes#task_not_found) error.

---

## Filtering tasks

import CodeSamplesAsyncGuideFilterByStatuses1 from '/snippets/samples/code_samples_async_guide_filter_by_statuses_1.mdx';
import CodeSamplesAsyncGuideFilterByStatuses2 from '/snippets/samples/code_samples_async_guide_filter_by_statuses_2.mdx';
import CodeSamplesAsyncGuideMultipleFilters1 from '/snippets/samples/code_samples_async_guide_multiple_filters_1.mdx';

Querying the [get tasks endpoint](/reference/api/tasks#get-tasks) returns all tasks that have not been deleted. This unfiltered list may be difficult to parse in large projects.

This guide shows you how to use query parameters to filter tasks and obtain a more readable list of asynchronous operations.

Filtering batches with [the `/batches` route](/reference/api/batches) follows the same rules as filtering tasks. Keep in mind that many `/batches` parameters such as `uids` target the tasks included in batches, instead of the batches themselves.

## Requirements

- a command-line terminal
- a running Meilisearch project

## Filtering tasks with a single parameter

Use the get tasks endpoint to fetch all `canceled` tasks:

Use a comma to separate multiple values and fetch both `canceled` and `failed` tasks:

You may filter tasks based on `uid`, `status`, `type`, `indexUid`, `canceledBy`, or date. Consult the API reference for a full list of task filtering parameters.

## Combining filters

Use the ampersand character (`&`) to combine filters, equivalent to a logical `AND`:

This code sample returns all tasks in the `movies` index that have the type `documentAdditionOrUpdate` or `documentDeletion` and have the `status` of `processing`.

**`OR` operations between different filters are not supported.** e.g., you cannot view tasks which have a type of `documentAddition` **or** a status of `failed`.

---

## Managing the task database

import CodeSamplesGetAllTasksPaginating1 from '/snippets/samples/code_samples_get_all_tasks_paginating_1.mdx';
import CodeSamplesGetAllTasksPaginating2 from '/snippets/samples/code_samples_get_all_tasks_paginating_2.mdx';

By default, Meilisearch returns a list of 20 tasks for each request when you query the [get tasks endpoint](/reference/api/tasks#get-tasks). This guide shows you how to navigate the task list using query parameters.

Paginating batches with [the `/batches` route](/reference/api/batches) follows the same rules as paginating tasks.

## Configuring the number of returned tasks

Use the `limit` parameter to change the number of returned tasks:

Meilisearch will return a batch of tasks. Each batch of returned tasks is often called a "page" of tasks, and the size of that page is determined by `limit`:

```json
{
 "results": [
 …
 ],
 "total": 50,
 "limit": 2,
 "from": 10,
 "next": 8
}
```

It is possible none of the returned tasks are the ones you are looking for. In that case, you will need to use the [get all tasks request response](/reference/api/tasks#response) to navigate the results.

## Navigating the task list with `from` and `next`

Use the `next` value included in the response to your previous query together with `from` to fetch the next set of results:

This will return a new batch of tasks:

```json
{
 "results": [
 …
 ],
 "total": 50,
 "limit": 2,
 "from": 8,
 "next": 6
}
```

When the value of `next` is `null`, you have reached the final set of results.

Use `from` and `limit` together with task filtering parameters to navigate filtered task lists.

---

## Using task webhooks

This guide teaches you how to configure a single webhook via instance options to notify a URL when Meilisearch completes a [task](/learn/async/asynchronous_operations).

If you are using Cloud or need to configure multiple webhooks, use the [`/webhooks` API route](/reference/api/webhooks) instead.

## Requirements

- a command-line console
- a self-hosted Meilisearch instance
- a server configured to receive POST requests with an ndjson payload

## Configure the webhook URL

Restart your Meilisearch instance and provide the webhook URL to `--task-webhook-URL`:

```sh
Meilisearch --task-webhook-url http://localhost:8000
```

You may also define the webhook URL with environment variables or in the configuration file with `MEILI_TASK_WEBHOOK_URL`.

## Optional: configure an authorization header

Depending on your setup, you may need to provide an authorization header. Provide it to `task-webhook-authorization-header`:

```sh
Meilisearch --task-webhook-url http://localhost:8000 --task-webhook-authorization-header Bearer aSampleMasterKey
```

## Test the webhook

A common asynchronous operation is adding or updating documents to an index. The following example adds a test document to our `books` index:

```sh
curl \
 -X POST 'MEILISEARCH_URL/indexes/books/documents' \
 -H 'Content-Type: application/json' \
 --data-binary '[
 {
 "id": 1,
 "title": "Nuestra parte de noche",
 "author": "Mariana Enríquez"
 }
 ]'
```

When Meilisearch finishes indexing this document, it will send a POST request the URL you configured with `--task-webhook-url`. The request body will be one or more task objects in [ndjson](https://github.com/ndjson/ndjson-spec) format:

```ndjson
{"uid":4,"indexUid":"books","status":"succeeded","type":"documentAdditionOrUpdate","canceledBy":null,"details.receivedDocuments":1,"details.indexedDocuments":1,"duration":"PT0.001192S","enqueuedAt":"2022-08-04T12:28:15.159167Z","startedAt":"2022-08-04T12:28:15.161996Z","finishedAt":"2022-08-04T12:28:15.163188Z"}
```

If Meilisearch has batched multiple tasks, it will only trigger the webhook once all tasks in a batch are finished. In this case, the response payload will include all tasks, each separated by a new line:

```ndjson
{"uid":4,"indexUid":"books","status":"succeeded","type":"documentAdditionOrUpdate","canceledBy":null,"details.receivedDocuments":1,"details.indexedDocuments":1,"duration":"PT0.001192S","enqueuedAt":"2022-08-04T12:28:15.159167Z","startedAt":"2022-08-04T12:28:15.161996Z","finishedAt":"2022-08-04T12:28:15.163188Z"}
{"uid":5,"indexUid":"books","status":"succeeded","type":"documentAdditionOrUpdate","canceledBy":null,"details.receivedDocuments":1,"details.indexedDocuments":1,"duration":"PT0.001192S","enqueuedAt":"2022-08-04T12:28:15.159167Z","startedAt":"2022-08-04T12:28:15.161996Z","finishedAt":"2022-08-04T12:28:15.163188Z"}
{"uid":6,"indexUid":"books","status":"succeeded","type":"documentAdditionOrUpdate","canceledBy":null,"details.receivedDocuments":1,"details.indexedDocuments":1,"duration":"PT0.001192S","enqueuedAt":"2022-08-04T12:28:15.159167Z","startedAt":"2022-08-04T12:28:15.161996Z","finishedAt":"2022-08-04T12:28:15.163188Z"}
```

---

## Working with tasks

import CodeSamplesAddMoviesJson1 from '/snippets/samples/code_samples_add_movies_json_1.mdx';
import CodeSamplesGetTask1 from '/snippets/samples/code_samples_get_task_1.mdx';

[Many Meilisearch operations are processed asynchronously](/learn/async/asynchronous_operations) in a task. Asynchronous tasks allow you to make resource-intensive changes to your Meilisearch project without any downtime for users.

In this tutorial, you'll use the Meilisearch API to add documents to an index, and then monitor its status.

## Requirements

- a running Meilisearch project
- a command-line console

## Adding a task to the task queue

Operations that require indexing, such as adding and updating documents or changing an index's settings, will always generate a task.

Start by creating an index, then add a large number of documents to this index:

Instead of processing your request immediately, Meilisearch will add it to a queue and return a summarized task object:

```json
{
 "taskUid": 0,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "documentAdditionOrUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

The summarized task object is confirmation your request has been accepted. It also gives you information you can use to monitor the status of your request, such as the `taskUid`.

You can add documents to a new Cloud index using the Cloud interface. To get the `taskUid` of this task, visit the "Task" overview and look for a "Document addition or update" task associated with your newly created index.

## Monitoring task status

Meilisearch processes tasks in the order they were added to the queue. You can check the status of a task using the Cloud interface or the Meilisearch API.

### Monitoring task status in the Cloud interface

Log into your [Cloud](https://meilisearch.com/cloud) account and navigate to your project. Click the "Tasks" link in the project menu:

![Cloud menu with "Tasks" highlighted](/assets/images/cloud-tasks-tutorial/01-tasks-menu.png)

This will lead you to the task overview, which shows a list of all batches enqueued, processing, and completed in your project:

![A table listing multiple Cloud tasks](/assets/images/cloud-tasks-tutorial/02-tasks-table.png)

All Meilisearch tasks are processed in batches. When the batch containing your task changes its `status` to `succeeded`, Meilisearch has finished processing your request.

If the `status` changes to `failed`, Meilisearch was not able to fulfill your request. Check the object's `error` field for more information.

### Monitoring task status with the Meilisearch API

Use the `taskUid` from your request's response to check the status of a task:

This will return the full task object:

```json
{
 "uid": 4,
 "indexUid" :"movie",
 "status": "succeeded",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 …
 },
 "error": null,
 "duration": "PT0.001192S",
 "enqueuedAt": "2022-08-04T12:28:15.159167Z",
 "startedAt": "2022-08-04T12:28:15.161996Z",
 "finishedAt": "2022-08-04T12:28:15.163188Z"
}
```

If the task is still `enqueued` or `processing`, wait a few moments and query the database once again. You may also [set up a webhook listener](/reference/api/webhooks).

When `status` changes to `succeeded`, Meilisearch has finished processing your request.

If the task `status` changes to `failed`, Meilisearch was not able to fulfill your request. Check the task object's `error` field for more information.

## Conclusion

You have seen what happens when an API request adds a task to the task queue, and how to check the status of a that task. Consult the [task API reference](/reference/api/tasks) and the [asynchronous operations explanation](/learn/async/asynchronous_operations) for more information on how tasks work.

---

## What is conversational search?

Conversational search is an AI-powered search feature that allows users to ask questions in everyday language and receive answers based on the information in Meilisearch's indexes.

## When to use conversational vs traditional search

Use conversational search when:

- Users need easy-to-read answers to specific questions
- You are handling informational-dense content, such as knowledge bases
- Natural language interaction improves user experience

Use traditional search when:

- Users need to browse multiple options, such as an ecommerce website
- Approximate answers are not acceptable
- Your users need very quick responses

Conversational search is still in early development. Conversational agents may occasionally hallucinate inaccurate and misleading information, so it is important to closely monitor it in production environments.

## Conversational search user workflow

### Traditional search workflow

1. User enters keywords
2. Meilisearch returns matching documents
3. User reviews results to find answers

### Conversational search workflow

1. User asks a question in natural language
2. Meilisearch retrieves relevant documents
3. AI generates a direct answer based on those documents

## Implementation strategies

### Retrieval Augmented Generation (RAG)

In the majority of cases, you should use the [`/chats` route](/reference/api/chats) to build a Retrieval Augmented Generation (RAG) pipeline. RAGs excel when working with unstructured data and emphasise high-quality responses.

Meilisearch's chat completions API consolidates RAG creation into a single process:

1. **Query understanding**: automatically transforms questions into search parameters
2. **Hybrid retrieval**: combines keyword and semantic search for better relevancy
3. **Answer generation**: uses your chosen LLM to generate responses
4. **Context management**: maintains conversation history by constantly pushing the full conversation to the dedicated tool

Follow the [chat completions tutorial](/learn/chat/getting_started_with_chat) for information on how to implement a RAG with Meilisearch.

### Model Context Protocol (MCP)

An alternative method is using a Model Context Protocol (MCP) server. MCPs are designed for broader uses that go beyond answering questions, but can be useful in contexts where having up-to-date data is more important than comprehensive answers.

Follow the [dedicated MCP guide](/guides/ai/mcp) if you want to implement it in your application.

---

## Getting started with conversational search

To successfully implement a conversational search interface you must follow three steps: configure indexes for chat usage, create a chat workspaces, and build a chat interface.

## Prerequisites

Before starting, ensure you have:

- A [secure](/learn/security/basic_security) Meilisearch >= v1.15.1 project
- An API key from an LLM provider
- At least one index with searchable content

## Setup

### Enable the chat completions feature

First, enable the chat completions experimental feature:

[cURL example omitted]

Conversational search is still in early development. Conversational agents may occasionally hallucinate inaccurate and misleading information, so it is important to closely monitor it in production environments.

### Find your chat API key

When Meilisearch runs with a master key on an instance created after v1.15.1, it automatically generates a "Default Chat API Key" with `chatCompletions` and `search` permissions on all indexes. Check if you have the key using:

[cURL example omitted]

Look for the key with the description "Default Chat API Key".

#### Troubleshooting: Missing default chat API key

If your instance does not have a Default Chat API Key, create one manually:

[cURL example omitted]

## Configure your indexes

After activating the `/chats` route and obtaining an API key with chat permissions, configure the `chat` settings for each index you want to be searchable via chat UI:

[cURL example omitted]

- `description` gives the initial context of the conversation to the LLM. A good description improves relevance of the chat's answers
- `documentTemplate` defines the document data Meilisearch sends to the AI provider. This template outputs all searchable fields in your documents, which may not be ideal if your documents have many fields. Consult the best [document template best practices](/learn/ai_powered_search/document_template_best_practices) article for more guidance
- `documentTemplateMaxBytes` establishes a size limit for the document templates. Documents bigger than 400 bytes are truncated to ensure a good balance between speed and relevancy

## Configure a chat completions workspace

The next step is to create a workspace. Chat completion workspaces are isolated configurations targeting different use cases. Each workspace can:

- Use different embedding providers (OpenAI, Azure OpenAI, Mistral, Gemini, vLLM)
- Establish separate conversation contexts via baseline prompts
- Access a specific set of indexes

e.g., you may have one workspace for publicly visible data, and another for data only available for logged in users.

Create a workspace setting your LLM provider as its `source`:

[cURL example omitted]

Which fields are mandatory will depend on your chosen provider `source`. In most cases, you will have to provide an `apiKey` to access the provider.

`baseUrl` indicates the URL Meilisearch queries when users submit questions to your chat interface. This is only mandatory for Azure OpenAI and vLLM sources.

`prompts.system` gives the conversational search bot the baseline context of your users and their questions. [The `prompts` object accepts a few other fields](/reference/api/chats#prompts) that provide more information to improve how the agent uses the information it finds via Meilisearch. In real-life scenarios filling these fields would improve the quality of conversational search results.

## Send your first chat completions request

You have finished configuring your conversational search agent. To test everything is working as expected, send a streaming `curl` query to the chat completions API route:

[cURL example omitted]

- `model` is mandatory and must indicate a model supported by your chosen `source`
- `messages` contains the messages exchanged between the conversational search agent and the user
- `tools` sets up two optional but highly [recommended tools](/learn/chat/chat_tooling_reference):
 - `_meiliSearchProgress`: shows users what searches are being performed
 - `_meiliSearchSources`: displays the actual documents used to generate responses

If Meilisearch returns a stream of data containing the chat agent response, you have correctly configured Meilisearch for conversational search:

```sh
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"content":"Meilisearch"},"finish_reason":null}]}
```

If Meilisearch returns an error, consult the [troubleshooting section](#troubleshooting) to understand diagnose and fix the issues you encountered.

## Next steps

In this article, you have seen how to activate the chats completion route, prepare your indexes to serve as a base for your AI agent, and performed your first conversational search.

In most cases, i.e. only the beginning of adding conversational search to your application. Next, you are most likely going to want to add a graphical user interface to your application.

### Building a chat interface using the OpenAI SDK

Meilisearch's chat endpoint was designed to be OpenAI-compatible. This means you can use the official OpenAI SDK in any supported programming language, even if your provider is not OpenAI.

Integrating Meiliearch and the OpenAI SDK with JavaScript would look lik this:

```javascript JavaScript
import OpenAI from 'openai';

const client = new OpenAI({
 baseURL: 'MEILISEARCH_URL/chats/WORKSPACE_NAME',
 apiKey: 'PROVIDER_API_KEY',
});

const completion = await client.chat.completions.create({
 model: 'PROVIDER_MODEL_UID',
 messages: [{ role: 'user', content: 'USER_PROMPT' }]
});

for await (const chunk of completion) {
 console.log(chunk.choices[0]?.delta?.content || '');
}
```

Take particular note of the last lines, which output the streamed responses to the browser console. In a real-life application, you would instead print the response chunks to the user interface.

## Troubleshooting

### Common issues and solutions

#### Empty reply from server (curl error 52)

**Causes:**

- Meilisearch not started with a master key
- Experimental features not enabled
- Missing authentication in requests

**Solution:**

1. Restart Meilisearch with a master key: `Meilisearch --master-key yourKey`
2. Enable experimental features (see setup instructions above)
3. Include Authorization header in all requests

#### "Invalid API key" error

**Cause:** Using the wrong type of API key

**Solution:**

- Use either the master key or the "Default Chat API Key"
- Don't use search or admin API keys for chat endpoints
- Find your chat key: `curl MEILISEARCH_URL/keys -H "Authorization: Bearer MEILISEARCH_KEY"`

#### "Socket connection closed unexpectedly"

**Cause:** Usually means the OpenAI API key is missing or invalid in workspace settings

**Solution:**

1. Check workspace configuration:

 ```bash
 curl MEILISEARCH_URL/chats/WORKSPACE_NAME/settings \
 -H "Authorization: Bearer MEILISEARCH_KEY"
 ```

2. Update with valid API key:

 ```bash
 curl -X PATCH MEILISEARCH_URL/chats/WORKSPACE_NAME/settings \
 -H "Authorization: Bearer MEILISEARCH_KEY" \
 -H "Content-Type: application/json" \
 -d '{"apiKey": "your-valid-api-key"}'
 ```

#### Chat not searching the database

**Cause:** Missing Meilisearch tools in the request

**Solution:**

- Include `_meiliSearchProgress` and `_meiliSearchSources` tools in your request
- Ensure indexes have proper chat descriptions configured

---

## Configuring index settings

This tutorial will show you how to check and change an index setting using the [Cloud](https://cloud.meilisearch.com/projects/) interface.

## Requirements

- an active [Cloud](https://cloud.meilisearch.com/projects/) account
- a Cloud project with at least one index

## Accessing a project's index settings

Log into your Meilisearch account and navigate to your project. Then, click on "Indexes":

 <img src="/assets/images/cloud-index-settings/01-indexes-tab.png" alt="The main menu of the project view in the Cloud interface. Menu items include 'Indexes' among other options such as 'Settings' and 'Analytics'." />

Find the index you want to configure and click on its "Settings" button:

 <img src="/assets/images/cloud-index-settings/02-index-settings.png" alt="A list of indexes in a Cloud project. It shows an index named 'books' along with a few icons and buttons. One of these buttons is 'Settings.'" />

## Checking a setting's current value

Using the menu on the left-hand side, click on "Attributes":

 <img src="/assets/images/cloud-index-settings/03-general-settings.png" alt="The index configuration overview together with a menu with links to pages dedicated to various index settings." />

The first setting is "Searchable attributes" and lists all attributes in your dataset's documents:

 <img src="/assets/images/cloud-index-settings/04-searchable-attributes-default.png" alt="The 'Searchable attributes' configuration section showing six attributes. One of them, 'id' is this index's primary key." />

Clicking on other settings will show you similar interfaces that allow visualizing and editing all Meilisearch index settings.

## Updating a setting

All documents include a primary key attribute. In most cases, this attribute does not contain information relevant for searches, so you can improve your application's search by explicitly removing it from the searchable attributes list.

Find your primary key, then click on the bin icon:

 <img src="/assets/images/cloud-index-settings/05-searchable-attributes-delete.png" alt="The same 'Searchable attributes' list as before, with the bin-shaped 'delete' icon highlighted." />

Meilisearch will display a pop-up window asking you to confirm you want to remove the attribute from the searchable attributes list. Click on "Yes, remove attribute":

 <img src="/assets/images/cloud-index-settings/06-searchable-attributes-confirm-deletion.png" alt="A pop-up window over the index settings interface. It reads: 'Are you sure you want to remove the attribute id?' Below it are two buttons: 'Cancel' and 'Yes, remove attribute'." />

Most updates to an index's settings will cause Meilisearch to re-index all its data. Wait a few moments until this operation is complete. You are not allowed to update any index settings during this time.

Once Meilisearch finishes indexing, the primary key will no longer appear in the searchable attributes list:

 <img src="/assets/images/cloud-index-settings/07-searchable-attributes-attribute-deleted.png" alt="The same 'Searchable attributes' list as before. It only contains five searchable attributes after removing the primary key." />

If you deleted the wrong attribute, click on "Add attributes" to add it back to the list. You may also click on "Reset to default", which will bring back the searchable list to its original state when you first added your first document to this index:

 <img src="/assets/images/cloud-index-settings/08-searchable-attributes-reset.png" alt="The same 'Searchable attributes' list as before. Two buttons on its top-right corner are highlighted: 'Reset to default' and 'Add attributes'." />

## Conclusion

You have used the Cloud interface to check the value of an index setting. This revealed an opportunity to improve your project's performance, so you updated this index setting to make your application better and more responsive.

This tutorial used the "Searchable attributes" setting, but the procedure is the same no matter which index setting you are editing.

## What's next

If you prefer to access the settings API directly through your console, you can also [configure index settings using the Cloud API](/learn/configuration/configuring_index_settings_api).

For a comprehensive reference of all index settings, consult the [settings API reference](/reference/api/settings).

---

## Configuring index settings with the Meilisearch API

import CodeSamplesIndexSettingsTutorialApiGetSetting1 from '/snippets/samples/code_samples_index_settings_tutorial_api_get_setting_1.mdx';
import CodeSamplesIndexSettingsTutorialApiPutSetting1 from '/snippets/samples/code_samples_index_settings_tutorial_api_put_setting_1.mdx';
import CodeSamplesIndexSettingsTutorialApiTask1 from '/snippets/samples/code_samples_index_settings_tutorial_api_task_1.mdx';

This tutorial shows how to check and change an index setting using one of the setting subroutes of the Meilisearch API.

If you are Cloud user, you may also [configure index settings using the Cloud interface](/learn/configuration/configuring_index_settings).

## Requirements

- a new [Cloud](https://cloud.meilisearch.com/projects/) project or a self-hosted Meilisearch instance with at least one index
- a command-line terminal with `curl` installed

## Getting the value of a single index setting

Start by checking the value of the searchable attributes index setting.

Use the GET endpoint of the `/settings/searchable-attributes` subroute, replacing `INDEX_NAME` with your index:

Depending on your setup, you might also need to replace `localhost:7700` with the appropriate address and port.

You should receive a response immediately:

```json
[
 "*"
]
```

If this is a new index, you should see the default value, \["*"\]. This indicates Meilisearch looks through all document attributes when searching.

## Updating an index setting

All documents include a primary key attribute. In most cases, this attribute does not contain any relevant data, so you can improve your application search experience by explicitly removing it from your searchable attributes list.

Use the PUT endpoint of the `/settings/searchable-attributes` subroute, replacing `INDEX_NAME` with your index and the sample attributes `"title"` and `"overview"` with attributes present in your dataset:

This time, Meilisearch will not process your request immediately. Instead, you will receive a summarized task object while the search engine works on updating your index setting as soon as it has enough resources:

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_NAME",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

Processing the index setting change might take some time, depending on how many documents you have in your index. Wait a few seconds and use the task object's `taskUid` to monitor the status of your request:

Meilisearch will respond with a task object:

```json
{
 "uid": 1,
 "indexUid": "INDEX_NAME",
 "status": "succeeded",
 "type": "settingsUpdate",
 …
}
```

If `status` is `enqueued` or `processed`, wait a few more moments and check the task status again. If `status` is `failed`, make sure you have used a valid index and attributes, then try again.

If task `status` is `succeeded`, you successfully updated your index's searchable attributes. Use the subroute to check the new setting's value:

Meilisearch should return an array with the new values:

```json
[
 "title",
 "overview"
]
```

## Conclusion

You have used the Meilisearch API to check the value of an index setting. This revealed an opportunity to improve your project's performance, so you updated this index setting to make your application better and more responsive.

This tutorial used the searchable attributes setting, but the procedure is the same no matter which index setting you are editing.

For a comprehensive reference of all index settings, consult the [settings API reference](/reference/api/settings).

---

## Exporting and importing dumps

import CodeSamplesPostDump1 from '/snippets/samples/code_samples_post_dump_1.mdx';
import CodeSamplesGetTask1 from '/snippets/samples/code_samples_get_task_1.mdx';

A [dump](/learn/data_backup/snapshots_vs_dumps#dumps) is a compressed file containing an export of your Meilisearch instance. Use dumps to migrate to new Meilisearch versions. This tutorial shows you how to create and import dumps.

Creating a dump is also referred to as exporting it. Launching Meilisearch with a dump is referred to as importing it.

## Creating a dump

### Creating a dump in Cloud

**You cannot manually export dumps in Cloud**. To [migrate your project to the most recent Meilisearch release](/learn/update_and_migration/updating), use the Cloud interface:

 <img src="/assets/images/cloud-dumps/01-export-dump.png" alt="The General settings interface displaying various data fields relating to a Cloud project. One of them reads 'Meilisearch version'. Its value is 'v1.6.2'. Next to the value is a button 'Update to v1.7.0'" />

If you need to create a dump for reasons other than upgrading, contact the support team via the Cloud interface or the [official Meilisearch Discord server](https://discord.meilisearch.com).

### Creating a dump in a self-hosted instance

To create a dump, use the [create a dump endpoint](/reference/api/dump#create-a-dump):

This will return a [summarized task object](/learn/async/asynchronous_operations#summarized-task-objects) that you can use to check the status of your dump.

```json
{
 "taskUid": 1,
 "indexUid": null,
 "status": "enqueued",
 "type": "dumpCreation",
 "enqueuedAt": "2022-06-21T16:10:29.217688Z"
}
```

The dump creation process is an asynchronous task that takes time proportional to the size of your database. Replace `1` with the `taskUid` returned by the previous command:

This should return an object with detailed information about the dump operation:

```json
{
 "uid": 1,
 "indexUid": null,
 "status": "succeeded",
 "type": "dumpCreation",
 "canceledBy": null,
 "details": {
 "dumpUid": "20220621-161029217"
 },
 "error": null,
 "duration": "PT0.025872S",
 "enqueuedAt": "2022-06-21T16:10:29.217688Z",
 "startedAt": "2022-06-21T16:10:29.218297Z",
 "finishedAt": "2022-06-21T16:10:29.244169Z"
}
```

All indexes of the current instance are exported along with their documents and settings and saved as a single `.dump` file. The dump also includes any tasks registered before Meilisearch starts processing the dump creation task.

Once the task `status` changes to `succeeded`, find the dump file in [the dump directory](/learn/self_hosted/configure_meilisearch_at_launch#dump-directory). By default, this folder is named `dumps` and can be found in the same directory where you launched Meilisearch.

If a dump file is visible in the file system, the dump process was successfully completed. **Meilisearch will never create a partial dump file**, even if you interrupt an instance while it is generating a dump.

Since the `key` field depends on the master key, it is not propagated to dumps. If a malicious user ever gets access to your dumps, they will not have access to your instance's API keys.

## Importing a dump

### Importing a dump in Cloud

You can import a dump into Meilisearch when creating a new project, below the plan selector:

 <img src="/assets/images/cloud-dumps/02-import-dump.png" alt="The project creation interface, with a few inputs fields: project name, region selection, and plan selection. Right below all of these, is a file upload button named 'Import .dump'" />

### Importing a dump in self-hosted instances

Import a dump by launching a Meilisearch instance with the [`--import-dump` configuration option](/learn/self_hosted/configure_meilisearch_at_launch#import-dump):

```bash
./Meilisearch --import-dump /dumps/20200813-042312213.dump
```

Depending on the size of your dump file, importing it might take a significant amount of time. You will only be able to access Meilisearch and its API once this process is complete.

Meilisearch imports all data in the dump file. If you have already added data to your instance, existing indexes with the same `uid` as an index in the dump file will be overwritten.

Do not use dumps to migrate from a new Meilisearch version to an older release. Doing so might lead to unexpected behavior.

---

## Exporting and using Snapshots

A [snapshot](/learn/data_backup/snapshots_vs_dumps#snapshots) is an exact copy of the Meilisearch database. Snapshots are useful as quick backups, but cannot be used to migrate to a new Meilisearch release.

This tutorial shows you how to schedule snapshot creation to ensure you always have a recent backup of your instance ready to use. You will also see how to start Meilisearch from this snapshot.

Cloud does not support snapshots.

## Scheduling periodic snapshots

It is good practice to create regular backups of your Meilisearch data. This ensures that you can recover from critical failures quickly in case your Meilisearch instance becomes compromised.

Use the [`--schedule-snapshot` configuration option](/learn/self_hosted/configure_meilisearch_at_launch#schedule-snapshot-creation) to create snapshots at regular time intervals:

```bash
Meilisearch --schedule-snapshot
```

The first snapshot is created on launch. You will find it in the [snapshot directory](/learn/self_hosted/configure_meilisearch_at_launch#snapshot-destination), `/snapshots`. Meilisearch will then create a new snapshot every 24 hours until you terminate your instance.

Meilisearch **automatically overwrites** old snapshots during snapshot creation. Only the most recent snapshot will be present in the folder at any given time.

In cases where your database is updated several times a day, it might be better to modify the interval between each new snapshot:

```bash
Meilisearch --schedule-snapshot=3600
```

This instructs Meilisearch to create a new snapshot once every hour.

If you need to generate a single snapshot without relaunching your instance, use [the `/snapshots` route](/reference/api/snapshots).

## Starting from a snapshot

To import snapshot data into your instance, launch Meilisearch using `--import-snapshot`:

```bash
Meilisearch --import-snapshot mySnapShots/data.ms.snapshot
```

Because snapshots are exact copies of your database, starting a Meilisearch instance from a snapshot is much faster than adding documents manually or starting from a dump.

For security reasons, Meilisearch will never overwrite an existing database. By default, Meilisearch will throw an error when importing a snapshot if there is any data in your instance.

You can change this behavior by specifying [`--ignore-snapshot-if-db-exists=true`](/learn/self_hosted/configure_meilisearch_at_launch#ignore-dump-if-db-exists). This will cause Meilisearch to launch with the existing database and ignore the dump without throwing an error.

---

## Snapshots and dumps

This article explains Meilisearch's two backup methods: snapshots and dumps.

## Snapshots

A snapshot is an exact copy of the Meilisearch database, located by default in `./data.ms`. [Use snapshots for quick and efficient backups of your instance](/learn/data_backup/snapshots).

The documents in a snapshot are already indexed and ready to go, greatly increasing import speed. However, snapshots are not compatible between different versions of Meilisearch. Snapshots are also significantly bigger than dumps.

In short, snapshots are a safeguard: if something goes wrong in an instance, you're able to recover and relaunch your database quickly. You can also schedule periodic snapshot creation.

## Dumps

A dump isn't an exact copy of your database like a snapshot. Instead, it is closer to a blueprint which Meilisearch can later use to recreate a whole instance from scratch.

Importing a dump requires Meilisearch to re-index all documents. This process uses a significant amount of time and memory proportional to the size of the database. Compared to the snapshots, importing a dump is a slow and inefficient operation.

At the same time, dumps are not bound to a specific Meilisearch version. This means dumps are ideal for migrating your data when you upgrade Meilisearch.

Use dumps to transfer data from an old Meilisearch version into a more recent release. Do not transfer data from a new release into a legacy Meilisearch version.

e.g., you can import a dump from Meilisearch v1.2 into v1.6 without any problems. Importing a dump generated in v1.7 into a v1.2 instance, however, can lead to unexpected behavior.

## Snapshots VS dumps

Both snapshots and dumps are data backups, but they serve different purposes.

Snapshots are highly efficient, but not portable between different versions of Meilisearch. **Use snapshots for periodic data backups.**

Dumps are portable between different Meilisearch versions, but not very efficient. **Use dumps when updating to a new Meilisearch release.**

---

## Concatenated and split queries

## Concatenated queries

When your search contains several words, Meilisearch applies a concatenation algorithm to it.

When searching for multiple words, a search is also done on the concatenation of those words. When concatenation is done on a search query containing multiple words, it will concatenate the words following each other. Thus, the first and third words will not be concatenated without the second word.

### Example

A search on `The news paper` will also search for the following concatenated queries:

- `Thenews paper`
- `the newspaper`
- `Thenewspaper`

This concatenation is done on a **maximum of 3 words**.

## Split queries

When you do a search, it **applies the splitting algorithm to every word** (_string separated by a space_).

This consists of finding the most interesting place to separate the words and to create a parallel search query with this proposition.

This is achieved by finding the best frequency of the separate words in the dictionary of all words in the dataset. It will look out that both words have a minimum of interesting results, and not just one of them.

Split words are not considered as multiple words in a search query because they must stay next to each other.

### Example

On a search on `newspaper`, it will split into `news` and `paper` and not into `new` and `spaper`.
A document containing `news` and `paper` separated by other words will not be relevant to the search.

---

## Data types

This article explains how Meilisearch handles the different types of data in your dataset.

**The behavior described here concerns only Meilisearch's internal processes** and can be helpful in understanding how the tokenizer works. Document fields remain unchanged for most practical purposes not related to Meilisearch's inner workings.

## String

String is the primary type for indexing data in Meilisearch. It enables to create the content in which to search. Strings are processed as detailed below.

String tokenization is the process of **splitting a string into a list of individual terms that are called tokens.**

A string is passed to a tokenizer and is then broken into separate string tokens. A token is a **word**.

### Tokenization

Tokenization relies on two main processes to identifying words and separating them into tokens: separators and dictionaries.

#### Separators

Separators are characters that indicate where one word ends and another word begins. In languages using the Latin alphabet, e.g., words are usually delimited by white space. In Japanese, word boundaries are more commonly indicated in other ways, such as appending particles like `に` and `で` to the end of a word.

There are two kinds of separators in Meilisearch: soft and hard. Hard separators signal a significant context switch such as a new sentence or paragraph. Soft separators only delimit one word from another but do not imply a major change of subject.

The list below presents some of the most common separators in languages using the Latin alphabet:

- **Soft spaces** (distance: 1): whitespaces, quotes, `'-' | '_' | '\'' | ':' | '/' | '\\' | '@' | '"' | '+' | '~' | '=' | '^' | '*' | '#'`
- **Hard spaces** (distance: 8): `'.' | ';' | ',' | '!' | '?' | '(' | ')' | '[' | ']' | '{' | '}'| '|'`

For more separators, including those used in other writing systems like Cyrillic and Thai, [consult this exhaustive list](https://docs.rs/charabia/0.8.3/src/charabia/separators.rs.html#16-62).

#### Dictionaries

For the tokenization process, dictionaries are lists of groups of characters which should be considered as single term. Dictionaries are particularly useful when identifying words in languages like Japanese, where words are not always marked by separator tokens.

Meilisearch comes with a number of general-use dictionaries for its officially supported languages. When working with documents containing many domain-specific terms, such as a legal documents or academic papers, providing a [custom dictionary](/reference/api/settings#dictionary) may improve search result relevancy.

### Distance

Distance plays an essential role in determining whether documents are relevant since [one of the ranking rules is the **proximity** rule](/learn/relevancy/relevancy). The proximity rule sorts the results by increasing distance between matched query terms. Then, two words separated by a soft space are closer and thus considered **more relevant** than two words separated by a hard space.

After the tokenizing process, each word is indexed and stored in the global dictionary of the corresponding index.

### Examples

To demonstrate how a string is split by space, let's say you have the following string as an input:

```
"Bruce Willis,Vin Diesel"
```

In the example above, the distance between `Bruce` and `Willis` is equal to **1**. The distance between `Vin` and `Diesel` is also **1**. However, the distance between `Willis` and `Vin` is equal to **8**. The same calculations apply to `Bruce` and `Diesel` (10), `Bruce` and `Vin` (9), and `Willis` and `Diesel` (9).

Let's see another example. Given two documents:

```json
[
 {
 "movie_id": "001",
 "description": "Bruce.Willis"
 },
 {
 "movie_id": "002",
 "description": "Bruce super Willis"
 }
]
```

When making a query on `Bruce Willis`, `002` will be the first document returned, and `001` will be the second one. This will happen because the proximity distance between `Bruce` and `Willis` is equal to **2** in the document `002`, whereas the distance between `Bruce` and `Willis` is equal to **8** in the document `001` since the full-stop character `.` is a hard space.

## Numeric

A numeric type (`integer`, `float`) is converted to a human-readable decimal number string representation. Numeric types can be searched as they are converted to strings.

You can add [custom ranking rules](/learn/relevancy/custom_ranking_rules) to create an ascending or descending sorting rule on a given attribute that has a numeric value in the documents.

You can also create [filters](/learn/filtering_and_sorting/filter_search_results). The `>`, `>=`, `<`, `<=`, and `TO` relational operators apply only to numerical values.

## Boolean

A Boolean value, which is either `true` or `false`, is received and converted to a lowercase human-readable text (`true` and `false`). Booleans can be searched as they are converted to strings.

## `null`

The `null` type can be pushed into Meilisearch but it **won't be taken into account for indexing**.

## Array

An array is an ordered list of values. These values can be of any type: number, string, boolean, object, or even other arrays.

Meilisearch flattens arrays and concatenates them into strings. Non-string values are converted as described in this article's previous sections.

### Example

The following input:

```json
[
 [
 "Bruce Willis",
 "Vin Diesel"
 ],
 "Kung Fu Panda"
]
```

Will be processed as if all elements were arranged at the same level:

```json
"Bruce Willis. Vin Diesel. Kung Fu Panda."
```

Once the above array has been flattened, it will be parsed exactly as explained in the [string example](/learn/engine/datatypes#examples).

## Objects

When a document field contains an object, Meilisearch flattens it and brings the object's keys and values to the root level of the document itself.

Keep in mind that the flattened objects represented here are an intermediary snapshot of internal processes. When searching, the returned document will keep its original structure.

In the example below, the `patient_name` key contains an object:

```json
{
 "id": 0,
 "patient_name": {
 "forename": "Imogen",
 "surname": "Temult"
 }
}
```

During indexing, Meilisearch uses dot notation to eliminate nested fields:

```json
{
 "id": 0,
 "patient_name.forename": "Imogen",
 "patient_name.surname": "Temult"
}
```

Using dot notation, no information is lost when flattening nested objects, regardless of nesting depth.

Imagine that the example document above includes an additional object, `address`, containing home and work addresses, each of which are objects themselves. After flattening, the document would look like this:

```json
{
 "id": 0,
 "patient_name.forename": "Imogen",
 "patient_name.surname": "Temult",
 "address.home.street": "Largo Isarco, 2",
 "address.home.postcode": "20139",
 "address.home.city": "Milano",
 "address.work.street": "Ca' Corner Della Regina, 2215",
 "address.work.postcode": "30135",
 "address.work.city": "Venezia"
}
```

Meilisearch's internal flattening process also eliminates nesting in arrays of objects. In this case, values are grouped by key. Consider the following document:

```json
{
 "id": 0,
 "patient_name": "Imogen Temult",
 "appointments": [
 {
 "date": "2022-01-01",
 "doctor": "Jester Lavorre",
 "ward": "psychiatry"
 },
 {
 "date": "2019-01-01",
 "doctor": "Dorian Storm"
 }
 ]
}
```

After flattening, it would look like this:

```json
{
 "id": 0,
 "patient_name": "Imogen Temult",
 "appointments.date": [
 "2022-01-01",
 "2019-01-01"
 ],
 "appointments.doctor": [
 "Jester Lavorre",
 "Dorian Storm"
 ],
 "appointments.ward": [
 "psychiatry"
 ]
}
```

Once all objects inside a document have been flattened, Meilisearch will continue processing it as described in the previous sections. e.g., arrays will be flattened, and numeric and boolean values will be turned into strings.

### Nested document querying and subdocuments

Meilisearch has no concept of subdocuments and cannot perform nested document querying. In the previous example, the relationship between an appointment's date and doctor is lost when flattening the `appointments` array:

```json
…
 "appointments.date": [
 "2022-01-01",
 "2019-01-01"
 ],
 "appointments.doctor": [
 "Jester Lavorre",
 "Dorian Storm"
 ],
…
```

This may lead to unexpected behavior during search. The following dataset shows two patients and their respective appointments:

```json
[
 {
 "id": 0,
 "patient_name": "Imogen Temult",
 "appointments": [
 {
 "date": "2022-01-01",
 "doctor": "Jester Lavorre"
 }
 ]
 },
 {
 "id": 1,
 "patient_name": "Caleb Widowgast",
 "appointments": [
 {
 "date": "2022-01-01",
 "doctor": "Dorian Storm"
 },
 {
 "date": "2023-01-01",
 "doctor": "Jester Lavorre"
 }
 ]
 }
]
```

The following query returns patients `0` and `1`:

```sh
curl \
 -X POST 'MEILISEARCH_URL/indexes/clinic_patients/search' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "q": "",
 "filter": "(appointments.date = 2022-01-01 AND appointments.doctor = 'Jester Lavorre')"
 }'
```

Meilisearch is unable to only return patients who had an appointment with `Jester Lavorre` in `2022-01-01`. Instead, it returns patients who had an appointment with `Jester Lavorre`, and patients who had an appointment in `2022-01-01`.

The best way to work around this limitation is reformatting your data. The above example could be fixed by merging appointment data in a new `appointmentsMerged` field so the relationship between appointment and doctor remains intact:

```json
[
 {
 "id": 0,
 "patient_name": "Imogen Temult",
 "appointmentsMerged": [
 "2022-01-01 Jester Lavorre"
 ]
 },
 {
 "id": 1,
 "patient_name": "Caleb Widowgast",
 "appointmentsMerged": [
 "2023-01-01 Jester Lavorre"
 "2022-01-01 Dorian Storm"
 ]
 }
]
```

## Possible tokenization issues

Even if it behaves exactly as expected, the tokenization process may lead to counterintuitive results in some cases, such as:

```
"S.O.S"
"George R. R. Martin"
10,3
```

For the two strings above, the full stops `.` will be considered as hard spaces.

`10,3` will be broken into two strings—`10` and `3`—instead of being processed as a numeric type.

---

## Prefix search

In Meilisearch, **you can perform a search with only a single letter as your query**. This is because we follow the philosophy of **prefix search**.

Prefix search is when document sorting starts by comparing the search query against the beginning of each word in your dataset. All documents with words that match the query term are added to the [bucket sort](https://en.wikipedia.org/wiki/Bucket_sort), before the [ranking rules](/learn/relevancy/ranking_rules) are applied sequentially.

In other words, prefix search means that it's not necessary to type a word in its entirety to find documents containing that word—you can just type the first one or two letters.

Prefix search is only performed on the last word in a search query—prior words must be typed out fully to get accurate results.

Searching by prefix (rather than using complete words) has a significant impact on search time. The shorter the query term, the more possible matches in the dataset.

### Example

Given a set of words in a dataset:

`film` `cinema` `movies` `show` `harry` `potter` `shine` `musical`

query: `s`:
response:

- `show`
- `shine`

but not

- `movies`
- `musical`

query: `sho`:
response:

- `show`

Meilisearch also handles typos while performing the prefix search. You can [read more about the typo rules on the dedicated page](/learn/relevancy/typo_tolerance_settings).

We also [apply splitting and concatenating on search queries](/learn/engine/concat).

---

## Storage

Meilisearch is in many ways a database: it stores indexed documents along with the data needed to return relevant search results.

## Database location

Meilisearch creates the database the moment you first launch an instance. By default, you can find it inside a `data.ms` folder located in the same directory as the `meilisearch` binary.

The database location can change depending on a number of factors, such as whether you have configured a different database path with the [`--db-path` instance option](/learn/self_hosted/configure_meilisearch_at_launch#database-path), or if you're using an OS virtualization tool like [Docker](https://docker.com).

## LMDB

Creating a database from scratch and managing it is hard work. It would make no sense to try and reinvent the wheel, so Meilisearch uses a storage engine under the hood. This allows the Meilisearch team to focus on improving search relevancy and search performance while abstracting away the complicated task of creating, reading, and updating documents on disk and in memory.

Our storage engine is called [Lightning Memory-Mapped Database](http://www.lmdb.tech/doc/) (LMDB for short). LMDB is a transactional key-value store written in C that was developed for OpenLDAP and has ACID properties. Though we considered other options, such as [Sled](https://github.com/spacejam/sled) and [RocksDB](https://rocksdb.org/), we chose LMDB because it provided us with the best combination of performance, stability, and features.

### Memory mapping

LMDB stores its data in a [memory-mapped file](https://en.wikipedia.org/wiki/Memory-mapped_file). All data fetched from LMDB is returned straight from the memory map, which means there is no memory allocation or memory copy during data fetches.

All documents stored on disk are automatically loaded in memory when Meilisearch asks for them. This ensures LMDB will always make the best use of the RAM available to retrieve the documents.

For the best performance, it is recommended to provide the same amount of RAM as the size the database takes on disk, so all the data structures can fit in memory.

### Understanding LMDB

The choice of LMDB comes with certain pros and cons, especially regarding database size and memory usage. We summarize the most important aspects of LMDB here, but check out this [blog post by LMDB's developers](https://www.symas.com/post/understanding-lmdb-database-file-sizes-and-memory-utilization) for more in-depth information.

#### Database size

When deleting documents from a Meilisearch index, you may notice disk space usage remains the same. This happens because LMDB internally marks that space as free, but does not make it available for the operating system at large. This design choice leads to better performance, as there is no need for periodic compaction operations. As a result, disk space occupied by LMDB (and thus by Meilisearch) tends to increase over time. It is not possible to calculate the precise maximum amount of space a Meilisearch instance can occupy.

#### Memory usage

Since LMDB is memory mapped, it is the operating system that manages the real memory allocated (or not) to Meilisearch.

Thus, if you run Meilisearch as a standalone program on a server, LMDB will use the maximum RAM it can use. In general, you should have the same amount of RAM as the space taken on disk by Meilisearch for optimal performance.

On the other hand, if you run Meilisearch along with other programs, the OS will manage memory based on everyone's needs. This makes Meilisearch's memory usage quite flexible when used in development.

**Virtual Memory != Real Memory**
Virtual memory is the disk space a program requests from the OS. It is not the memory that the program will actually use.

Meilisearch will always demand a certain amount of space to use as a [memory map](#memory-mapping). This space will be used as virtual memory, but the amount of real memory (RAM) used will be much smaller.

## Measured disk usage

The following measurements were taken using <a href="/assets/datasets/movies.json" download="movies.json">movies.json</a> an 8.6 MB JSON dataset containing 19,553 documents.

After indexing, the dataset size in LMDB is about 122MB. | Raw JSON | Meilisearch database size on disk | RAM usage | Virtual memory usage | | :--- | :--- | :--- | :--- | | 9.1 MB | 224 MB | ≃ 305 MB | 205 Gb (memory map) | This means the database is using **305 MB of RAM and 224 MB of disk space.** Note that [virtual memory](https://www.enterprisestorageforum.com/hardware/virtual-memory/) **refers only to disk space allocated by your computer for Meilisearch—it does not mean that it's actually in use by the database.** See [Memory Usage](#memory-usage) for more details.

These metrics are highly dependent on the machine i.e. running Meilisearch. Running this test on significantly underpowered machines is likely to give different results.

note: **there is no reliable way to predict the final size of a database**. This is true for just about any search engine on the market—we're just the only ones saying it out loud.

Database size is affected by a large number of criteria, including settings, relevancy rules, use of facets, the number of different languages present, and more.

---

## Faceted search

## Conjunctive facets

Conjunctive facets use the `AND` logical operator. When users select multiple values for a facet, returned results must contain all selected facet values.

With conjunctive facets, when a user selects `English` from the `language` facet, all returned books must be in English. If the user further narrows down the search by selecting `Fiction` and `Literature` as `genres`, all returned books must be in English and contain both `genres`.

```
"language = English AND genres = Fiction AND genres = Literature"
```

The GIF below shows how the facet count for `genres` updates to only include books that meet **all three conditions**.

![Selecting English books with 'Fiction' and 'Literature' as 'genres' for the books dataset](/assets/images/faceted-search/conjunctive-factes.gif)

## Disjunctive facets

Disjunctive facets use the `OR` logical operator. When users select multiple values for a facet, returned results must contain at least one of the selected values.

With disjunctive facets, when a user selects `Fiction`, and `Literature`, Meilisearch returns all books that are either `Fiction`, `Literature`, or both:

```
"genres = Fiction OR genres = Literature"
```

The GIF below shows the `books` dataset with disjunctive facets. Notice how the facet count for `genres` updates based on the selection.

![Selecting 'Fiction' and 'Literature' as 'genres' for the books dataset](/assets/images/faceted-search/disjunctive_facets.gif)

### Combining conjunctive and disjunctive facets

It is possible to create search queries with both conjunctive and disjunctive facets.

e.g., a user might select `English` and `French` from the `language` facet so they can see books written either in English or in French. This query uses an `OR` operator and is a disjunctive facet:

```
"language = English OR language = French"
```

The same user might also be interested in literary fiction books and select `Fiction` and `Literature` as `genres`. Since the user wants a specific combination of genres, their query uses an `AND` operator:

```
"genres = Fiction AND genres = Literature"
```

The user can combine these two filter expressions in one by wrapping them in parentheses and using an `AND` operator:

```
"(language = English OR language = French) AND (genres = Fiction AND genres = Literature)"
```

The GIF below shows the `books` dataset with conjunctive and disjunctive facets. Notice how the facet count for each facet updates based on the selection.

![Selecting 'Fiction' and 'Literature' as 'genres' for English books](/assets/images/faceted-search/conjunctive-and-disjunctive-facets.gif)

---

## Faceted search

You can use Meilisearch filters to build faceted search interfaces. This type of interface allows users to refine search results based on broad categories or facets. Faceted search provides users with a quick way to narrow down search results by selecting categories relevant to what they are looking for. A faceted navigation system is an **intuitive interface to display and navigate through content**.

Facets are common in ecommerce sites like Amazon. When users search for products, they are presented with a list of results and a list of facets which you can see on the sidebar in the image below:

 <a href="https://ecommerce.meilisearch.com/?utm_campaign=oss&utm_source=docs&utm_medium=faceted-search&utm_content=image">
 <img src="/assets/images/faceted-search/facets-ecommerce.png" alt="Meilisearch demo for an ecommerce website displaying faceting UI" />
 </a>

Faceted search interfaces often have a count of how many results belong to each facet. This gives users a visual clue of the range of results available for each facet.

### Filters or facets

Meilisearch does not differentiate between facets and filters. Facets are a specific use-case of filters, meaning you can use any attribute added to `filterableAttributes` as a facet. Whether something is a filter or a facet depends above all on UX and UI design.

## Example application

The Meilisearch ecommerce demo makes heavy use of faceting features to enable:

- Filtering products by category and brand
- Filtering products by price range and rating
- Searching through facet values (e.g. category)
- Sorting facet values (count or alphabetical order)

Check out the [ecommerce demo](https://ecommerce.meilisearch.com/?utm_campaign=oss&utm_source=docs&utm_medium=faceted-search&utm_content=link) and the [GitHub repository](https://github.com/meilisearch/ecommerce-demo/).

---

## Filter expression reference

import { NoticeTag } from '/snippets/notice_tag.mdx';

The `filter` search parameter expects a filter expression. Filter expressions are made of attributes, values, and several operators.

`filter` expects a **filter expression** containing one or more **conditions**. A filter expression can be written as a string, array, or mix of both.

## Data types

Filters accept numeric and string values. Empty fields or fields containing an empty array will be ignored.

Filters do not work with [`NaN`](https://en.wikipedia.org/wiki/NaN) and infinite values such as `inf` and `-inf` as they are [not supported by JSON](https://en.wikipedia.org/wiki/JSON#Data_types). It is possible to filter infinite and `NaN` values if you parse them as strings, except when handling [`_geo` fields](/learn/filtering_and_sorting/geosearch#preparing-documents-for-location-based-search).

For best results, enforce homogeneous typing across fields, especially when dealing with large numbers. Meilisearch does not enforce a specific schema when indexing data, but the filtering engine may coerce the type of `value`. This can lead to undefined behavior, such as when big floating-point numbers are coerced into integers.

## Conditions

Conditions are a filter's basic building blocks. They are written in the `attribute OPERATOR value` format, where:

- `attribute` is the attribute of the field you want to filter on
- `OPERATOR` can be `=`, `!=`, `>`, `>=`, `<`, `<=`, `TO`, `EXISTS`, `IN`, `NOT`, `AND`, or `OR`
- `value` is the value the `OPERATOR` should look for in the `attribute`

### Examples

A basic condition requesting movies whose `genres` attribute is equal to `horror`:

```
genres = horror
```

String values containing whitespace must be enclosed in single or double quotes:

```
director = 'Jordan Peele'
director = "Tim Burton"
```

## Filter operators

### Equality (`=`)

The equality operator (`=`) returns all documents containing a specific value for a given attribute:

```
genres = action
```

When operating on strings, `=` is case-insensitive.

The equality operator does not return any results for `null` and empty arrays.

### Inequality (`!=`)

The inequality operator (`!=`) returns all documents not selected by the equality operator. When operating on strings, `!=` is case-insensitive.

The following expression returns all movies without the `action` genre:

```
genres != action
```

### Comparison (`>`, `<`, `>=`, `<=`)

The comparison operators (`>`, `<`, `>=`, `<=`) select documents satisfying a comparison. Comparison operators apply to both numerical and string values.

The expression below returns all documents with a user rating above 85:

```
rating.users > 85
```

String comparisons resolve in lexicographic order: symbols followed by numbers followed by letters in alphabetic order. The expression below returns all documents released after the first day of 2004:

```
release_date > 2004-01-01
```

### `TO`

`TO` is equivalent to `>= AND <=`. The following expression returns all documents with a rating of 80 or above but below 90:

```
rating.users 80 TO 89
```

### `EXISTS`

The `EXISTS` operator checks for the existence of a field. Fields with empty or `null` values count as existing.

The following expression returns all documents containing the `release_date` field:

```
release_date EXISTS
```

The negated form of the above expression can be written in two equivalent ways:

```
release_date NOT EXISTS
NOT release_date EXISTS
```

#### Vector filters

When using AI-powered search, you may also use `EXISTS` to filter documents containing vector data:

- `_vectors EXISTS`: matches all documents with an embedding
- `_vectors.{embedder_name} EXISTS`: matches all documents with an embedding for the given embedder
- `_vectors.{embedder_name}.userProvided EXISTS`: matches all documents with a user-provided embedding on the given embedder
- `_vectors.{embedder_name}.documentTemplate EXISTS`: matches all documents with an embedding generated from a document template. Excludes user-provided embeddings
- `_vectors.{embedder_name}.regenerate EXISTS`: matches all documents with an embedding scheduled for regeneration
- `_vectors.{embedder_name}.fragments.{fragment_name} EXISTS`: matches all documents with an embedding generated from the given multimodal fragment. Excludes user-provided embeddings

`_vectors` is only compatible with the `EXISTS` operator.

### `IS EMPTY`

The `IS EMPTY` operator selects documents in which the specified attribute exists but contains empty values. The following expression only returns documents with an empty `overview` field:

```
overview IS EMPTY
```

`IS EMPTY` matches the following JSON values:

- `""`
- `[]`
- `{}`

Meilisearch does not treat `null` values as empty. To match `null` fields, use the [`IS NULL`](#is-null) operator.

Use `NOT` to build the negated form of `IS EMPTY`:

```
overview IS NOT EMPTY
NOT overview IS EMPTY
```

### `IS NULL`

The `IS NULL` operator selects documents in which the specified attribute exists but contains a `null` value. The following expression only returns documents with a `null` `overview` field:

```
overview IS NULL
```

Use `NOT` to build the negated form of `IS NULL`:

```
overview IS NOT NULL
NOT overview IS NULL
```

### `IN`

`IN` combines equality operators by taking an array of comma-separated values delimited by square brackets. It selects all documents whose chosen field contains at least one of the specified values.

The following expression returns all documents whose `genres` includes either `horror`, `comedy`, or both:

```
genres IN [horror, comedy]
genres = horror OR genres = comedy
```

The negated form of the above expression can be written as:

```
genres NOT IN [horror, comedy]
NOT genres IN [horror, comedy]
```

### `CONTAINS`

`CONTAINS` filters results containing partial matches to the specified string pattern, similar to a [SQL `LIKE`](https://dev.mysql.com/doc/refman/8.4/en/string-comparison-functions.html#operator_like).

The following expression returns all dairy products whose names contain `"kef"`:

```
dairy_products.name CONTAINS kef
```

The negated form of the above expression can be written as:

```
dairy_products.name NOT CONTAINS kef
NOT dairy_product.name CONTAINS kef
```

This is an experimental feature. Use the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "containsFilter": true
 }'
```

### `STARTS WITH`

`STARTS WITH` filters results whose values start with the specified string pattern.

The following expression returns all dairy products whose name start with `"kef"`:

```
dairy_products.name STARTS WITH kef
```

The negated form of the above expression can be written as:

```
dairy_products.name NOT STARTS WITH kef
NOT dairy_product.name STARTS WITH kef
```

### `NOT`

The negation operator (`NOT`) selects all documents that do not satisfy a condition. It has higher precedence than `AND` and `OR`.

The following expression will return all documents whose `genres` does not contain `horror` and documents with a missing `genres` field:

```
NOT genres = horror
```

## Filter expressions

You can build filter expressions by grouping basic conditions using `AND` and `OR`. Filter expressions can be written as strings, arrays, or a mix of both.

### Filter expression grouping operators

#### `AND`

`AND` connects two conditions and only returns documents that satisfy both of them. `AND` has higher precedence than `OR`.

The following expression returns all documents matching both conditions:

```
genres = horror AND director = 'Jordan Peele'
```

#### `OR`

`OR` connects two conditions and returns results that satisfy at least one of them.

The following expression returns documents matching either condition:

```
genres = horror OR genres = comedy
```

### Creating filter expressions with string operators and parentheses

Meilisearch reads string expressions from left to right. You can use parentheses to ensure expressions are correctly parsed.

For instance, if you want your results to only include `comedy` and `horror` documents released after March 1995, the parentheses in the following query are mandatory:

```
(genres = horror OR genres = comedy) AND release_date > 795484800
```

Failing to add these parentheses will cause the same query to be parsed as:

```
genres = horror OR (genres = comedy AND release_date > 795484800)
```

Translated into English, the above expression will only return comedies released after March 1995 or horror movies regardless of their `release_date`.

When creating an expression with a field name or value identical to a filter operator such as `AND` or `NOT`, you must wrap it in quotation marks: `title = "NOT" OR title = "AND"`.

### Creating filter expressions with arrays

Array expressions establish logical connectives by nesting arrays of strings. **Array filters can have a maximum depth of two.** Expressions with three or more levels of nesting will throw an error.

Outer array elements are connected by an `AND` operator. The following expression returns `horror` movies directed by `Jordan Peele`:

```
["genres = horror", "director = 'Jordan Peele'"]
```

Inner array elements are connected by an `OR` operator. The following expression returns either `horror` or `comedy` films:

```
[["genres = horror", "genres = comedy"]]
```

Inner and outer arrays can be freely combined. The following expression returns both `horror` and `comedy` movies directed by `Jordan Peele`:

```
[["genres = horror", "genres = comedy"], "director = 'Jordan Peele'"]
```

### Combining arrays and string operators

You can also create filter expressions that use both array and string syntax.

The following filter is written as a string and only returns movies not directed by `Jordan Peele` that belong to the `comedy` or `horror` genres:

```
"(genres = comedy OR genres = horror) AND director != 'Jordan Peele'"
```

You can write the same filter mixing arrays and strings:

```
[["genres = comedy", "genres = horror"], "NOT director = 'Jordan Peele'"]
```

---

## Filter search results

import CodeSamplesFilteringUpdateSettings1 from '/snippets/samples/code_samples_filtering_update_settings_1.mdx';
import CodeSamplesFilteringGuide1 from '/snippets/samples/code_samples_filtering_guide_1.mdx';
import CodeSamplesFilteringGuideNested1 from '/snippets/samples/code_samples_filtering_guide_nested_1.mdx';
import CodeSamplesFilteringGuide2 from '/snippets/samples/code_samples_filtering_guide_2.mdx';
import CodeSamplesFilteringGuide3 from '/snippets/samples/code_samples_filtering_guide_3.mdx';

In this guide you will see how to configure and use Meilisearch filters in a hypothetical movie database.

## Configure index settings

Suppose you have a collection of movies called `movie_ratings` containing the following fields:

```json
[
 {
 "id": 458723,
 "title": "Us",
 "director": "Jordan Peele",
 "release_date": 1552521600,
 "genres": [
 "Thriller",
 "Horror",
 "Mystery"
 ],
 "rating": {
 "critics": 86,
 "users": 73
 },
 },
 …
]
```

If you want to filter results based on an attribute, you must first add it to the `filterableAttributes` list:

**This step is mandatory and cannot be done at search time**. Updating `filterableAttributes` requires Meilisearch to re-index all your data, which will take an amount of time proportionate to your dataset size and complexity.

By default, `filterableAttributes` is empty. Filters do not work without first explicitly adding attributes to the `filterableAttributes` list.

## Use `filter` when searching

After updating the [`filterableAttributes` index setting](/reference/api/settings#filterable-attributes), you can use `filter` to fine-tune your search results.

`filter` is a search parameter you may use at search time. `filter` accepts [filter expressions](/learn/filtering_and_sorting/filter_expression_reference) built using any attributes present in the `filterableAttributes` list.

The following code sample returns `Avengers` movies released after 18 March 1995:

Use dot notation to filter results based on a document's [nested fields](/learn/engine/datatypes). The following query only returns thrillers with good user reviews:

You can also combine multiple conditions. e.g., you can limit your search so it only includes `Batman` movies directed by either `Tim Burton` or `Christopher Nolan`:

Here, the parentheses are mandatory: without them, the filter would return movies directed by `Tim Burton` and released after 1995 or any film directed by `Christopher Nolan`, without constraints on its release date. This happens because `AND` takes precedence over `OR`.

If you only want recent `Planet of the Apes` movies that weren't directed by `Tim Burton`, you can use this filter:

```
release_date > 1577884550 AND (NOT director = "Tim Burton" AND director EXISTS)
```

[Synonyms](/learn/relevancy/synonyms) don't apply to filters. Meaning, if you have `SF` and `San Francisco` set as synonyms, filtering by `SF` and `San Francisco` will show you different results.

---

## Geosearch

import CodeSamplesGeosearchGuideFilterSettings1 from '/snippets/samples/code_samples_geosearch_guide_filter_settings_1.mdx';
import CodeSamplesGeosearchGuideFilterUsage1 from '/snippets/samples/code_samples_geosearch_guide_filter_usage_1.mdx';
import CodeSamplesGeosearchGuideFilterUsage3 from '/snippets/samples/code_samples_geosearch_guide_filter_usage_3.mdx';
import CodeSamplesGeosearchGuideFilterUsage2 from '/snippets/samples/code_samples_geosearch_guide_filter_usage_2.mdx';
import CodeSamplesGeosearchGuideSortSettings1 from '/snippets/samples/code_samples_geosearch_guide_sort_settings_1.mdx';
import CodeSamplesGeosearchGuideSortUsage1 from '/snippets/samples/code_samples_geosearch_guide_sort_usage_1.mdx';
import CodeSamplesGeosearchGuideSortUsage2 from '/snippets/samples/code_samples_geosearch_guide_sort_usage_2.mdx';

Meilisearch allows you to filter and sort results based on their geographic location. This can be useful when you only want results within a specific area or when sorting results based on their distance from a specific location.

Due to Meilisearch allowing malformed `_geo` fields in the following versions (v0.27, v0.28 and v0.29), please ensure the `_geo` field follows the correct format.

## Preparing documents for location-based search

To start filtering documents based on their geographic location, you must make sure they contain a valid `_geo` or `_geojson` field. If you also want to sort documents geogeraphically, they must have a valid `_geo` field.

`_geo` and `_geojson` are reserved fields. If you include one of them in your documents, Meilisearch expects its value to conform to a specific format.

When using JSON and NDJSON, `_geo` must contain an object with two keys: `lat` and `lng`. Both fields must contain either a floating point number or a string indicating, respectively, latitude and longitude:

```json
{
 …
 "_geo": {
 "lat": 0.0,
 "lng": "0.0"
 }
}
```

`_geojson` must be an object whose contents follow the [GeoJSON specification](https://geojson.org/):

```json
{
 …
 "_geojson": {
 "type": "Feature",
 "geometry": {
 "type": "Point",
 "coordinates": [0.0, 0.0]
 }
 }
}
```

Meilisearch does not support transmeridian shapes. If your document includes a transmeridian shape, split it into two separate shapes grouped as a `MultiPolygon` or `MultiLine`. Transmeridian shapes are polygons or lines that cross the 180th meridian.

**Meilisearch does not support polygons with holes**. If your polygon consists of an external ring and an inner empty space, Meilisearch ignores the hole and treats the polygon as a solid shape.

### Using `_geo` and `_geojson` together

If your application requires both sorting by distance to a point and filtering by shapes other than a circle or a rectangle, you will need to add both `_geo` and `_geojson` to your documents.

When handling documents with both fields, Meilisearch:

- Ignores `_geojson` values when sorting
- Ignores `_geo` values when filtering with `_geoPolygon`
- Matches both `_geo` and `_geojson` values when filtering with `_geoRadius` and `_geoBoundingBox`

### Examples

Suppose we have a JSON array containing a few restaurants:

```json
[
 {
 "id": 1,
 "name": "Nàpiz' Milano",
 "address": "Viale Vittorio Veneto, 30, 20124, Milan, Italy",
 "type": "pizza",
 "rating": 9
 },
 {
 "id": 2,
 "name": "Bouillon Pigalle",
 "address": "22 Bd de Clichy, 75018 Paris, France",
 "type": "french",
 "rating": 8
 },
 {
 "id": 3,
 "name": "Artico Gelateria Tradizionale",
 "address": "Via Dogana, 1, 20123 Milan, Italy",
 "type": "ice cream",
 "rating": 10
 }
]
```

Our restaurant dataset looks like this once we add `_geo` data:

```json
[
 {
 "id": 1,
 "name": "Nàpiz' Milano",
 "address": "Viale Vittorio Veneto, 30, 20124, Milan, Italy",
 "type": "pizza",
 "rating": 9,
 "_geo": {
 "lat": 45.4777599,
 "lng": 9.1967508
 }
 },
 {
 "id": 2,
 "name": "Bouillon Pigalle",
 "address": "22 Bd de Clichy, 75018 Paris, France",
 "type": "french",
 "rating": 8,
 "_geo": {
 "lat": 48.8826517,
 "lng": 2.3352748
 }
 },
 {
 "id": 3,
 "name": "Artico Gelateria Tradizionale",
 "address": "Via Dogana, 1, 20123 Milan, Italy",
 "type": "ice cream",
 "rating": 10,
 "_geo": {
 "lat": 45.4632046,
 "lng": 9.1719421
 }
 }
]
```

Trying to index a dataset with one or more documents containing badly formatted `_geo` values will cause Meilisearch to throw an [`invalid_document_geo_field`](/reference/errors/error_codes#invalid_document_geo_field) error. In this case, the update will fail and no documents will be added or modified.

### Using `_geo` with CSV

If your dataset is formatted as CSV, the file header must have a `_geo` column. Each row in the dataset must then contain a column with a comma-separated string indicating latitude and longitude:

```csv
"id:number","name:string","address:string","type:string","rating:number","_geo:string"
"1","Nàpiz Milano","Viale Vittorio Veneto, 30, 20124, Milan, Italy","pizzeria",9,"45.4777599,9.1967508"
"2","Bouillon Pigalle","22 Bd de Clichy, 75018 Paris, France","french",8,"48.8826517,2.3352748"
"3","Artico Gelateria Tradizionale","Via Dogana, 1, 20123 Milan, Italy","ice cream",10,"48.8826517,2.3352748"
```

CSV files do not support the `_geojson` attribute.

## Filtering results with `_geoRadius`, `_geoBoundingBox`, and `_geoPolygon`

You can use `_geo` and `_geojson` data to filter queries so you only receive results located within a given geographic area.

### Configuration

To filter results based on their location, you must add `_geo` or `_geojson` to the `filterableAttributes` list:

Meilisearch will rebuild your index whenever you update `filterableAttributes`. Depending on the size of your dataset, this might take a considerable amount of time.

[You can read more about configuring `filterableAttributes` in our dedicated filtering guide.](/learn/filtering_and_sorting/filter_search_results)

### Usage

Use the [`filter` search parameter](/reference/api/search#filter) along with `_geoRadius` and `_geoBoundingBox`. These are special filter rules that ensure Meilisearch only returns results located within a specific geographic area. If you are using GeoJSON for your documents, you may also filter results with `_geoPolygon`.

### `_geoRadius`

```
_geoRadius(lat, lng, distance_in_meters, resolution)
```

### `_geoBoundingBox`

```
_geoBoundingBox([LAT, LNG], [LAT, LNG])
```

### `_geoPolygon`

```
_geoPolygon([LAT, LNG], [LAT, LNG], [LAT, LNG], …)
```

### Examples

Using our <a id="downloadRestaurants" href="/assets/datasets/restaurants.json" download="restaurants.json">example dataset</a>, we can search for places to eat near the center of Milan with `_geoRadius`:

We also make a similar query using `_geoBoundingBox`:

And with `_geoPolygon`:

```json
[
 {
 "id": 1,
 "name": "Nàpiz' Milano",
 "address": "Viale Vittorio Veneto, 30, 20124, Milan, Italy",
 "type": "pizza",
 "rating": 9,
 "_geo": {
 "lat": 45.4777599,
 "lng": 9.1967508
 }
 },
 {
 "id": 3,
 "name": "Artico Gelateria Tradizionale",
 "address": "Via Dogana, 1, 20123 Milan, Italy",
 "type": "ice cream",
 "rating": 10,
 "_geo": {
 "lat": 45.4632046,
 "lng": 9.1719421
 }
 }
]
```

It is also possible to combine `_geoRadius`, `_geoBoundingBox`, and `_geoPolygon` with other filters. We can narrow down our previous search so it only includes pizzerias:

```json
[
 {
 "id": 1,
 "name": "Nàpiz' Milano",
 "address": "Viale Vittorio Veneto, 30, 20124, Milan, Italy",
 "type": "pizza",
 "rating": 9,
 "_geo": {
 "lat": 45.4777599,
 "lng": 9.1967508
 }
 }
]
```

`_geo`, `_geoDistance`, and `_geoPoint` are not valid filter rules. Trying to use any of them with the `filter` search parameter will result in an [`invalid_search_filter`](/reference/errors/error_codes#invalid_search_filter) error.

## Sorting results with `_geoPoint`

### Configuration

Before using geosearch for sorting, you must add the `_geo` attribute to the [`sortableAttributes` list](/learn/filtering_and_sorting/sort_search_results):

It is not possible to sort documents based on the `_geojson` attribute.

### Usage

```
_geoPoint(0.0, 0.0):asc
```

### Examples

The `_geoPoint` sorting function can be used like any other sorting rule. We can order documents based on how close they are to the Eiffel Tower:

With our <a id="downloadRestaurants" href="/assets/datasets/restaurants.json" download="restaurants.json">restaurants dataset</a>, the results look like this:

```json
[
 {
 "id": 2,
 "name": "Bouillon Pigalle",
 "address": "22 Bd de Clichy, 75018 Paris, France",
 "type": "french",
 "rating": 8,
 "_geo": {
 "lat": 48.8826517,
 "lng": 2.3352748
 }
 },
 {
 "id": 3,
 "name": "Artico Gelateria Tradizionale",
 "address": "Via Dogana, 1, 20123 Milan, Italy",
 "type": "ice cream",
 "rating": 10,
 "_geo": {
 "lat": 45.4632046,
 "lng": 9.1719421
 }
 },
 {
 "id": 1,
 "name": "Nàpiz' Milano",
 "address": "Viale Vittorio Veneto, 30, 20124, Milan, Italy",
 "type": "pizza",
 "rating": 9,
 "_geo": {
 "lat": 45.4777599,
 "lng": 9.1967508
 }
 }
]
```

`_geoPoint` also works when used together with other sorting rules. We can sort restaurants based on their proximity to the Eiffel Tower and their rating:

```json
[
 {
 "id": 2,
 "name": "Bouillon Pigalle",
 "address": "22 Bd de Clichy, 75018 Paris, France",
 "type": "french",
 "rating": 8,
 "_geo": {
 "lat": 48.8826517,
 "lng": 2.3352748
 }
 },
 {
 "id": 3,
 "name": "Artico Gelateria Tradizionale",
 "address": "Via Dogana, 1, 20123 Milan, Italy",
 "type": "ice cream",
 "rating": 10,
 "_geo": {
 "lat": 45.4632046,
 "lng": 9.1719421
 }
 },
 {
 "id": 1,
 "name": "Nàpiz' Milano",
 "address": "Viale Vittorio Veneto, 30, 20124, Milan, Italy",
 "type": "pizza",
 "rating": 9,
 "_geo": {
 "lat": 45.4777599,
 "lng": 9.1967508
 }
 }
]
```

---

## Search with facets

import CodeSamplesFacetedSearchUpdateSettings1 from '/snippets/samples/code_samples_faceted_search_update_settings_1.mdx';
import CodeSamplesFacetedSearch1 from '/snippets/samples/code_samples_faceted_search_1.mdx';
import CodeSamplesFacetSearch2 from '/snippets/samples/code_samples_facet_search_2.mdx';
import CodeSamplesFacetSearch3 from '/snippets/samples/code_samples_facet_search_3.mdx';

In Meilisearch, facets are a specialized type of filter. This guide shows you how to configure facets and use them when searching a database of books. It also gives you instruction on how to get

## Requirements

- a Meilisearch project
- a command-line terminal

## Configure facet index settings

First, create a new index using this <a id="downloadBooks" href="/assets/datasets/books.json" download="books.json">books dataset</a>. Documents in this dataset have the following fields:

```json
{
 "id": 5,
 "title": "Hard Times",
 "genres": ["Classics","Fiction", "Victorian", "Literature"],
 "publisher": "Penguin Classics",
 "language": "English",
 "author": "Charles Dickens",
 "description": "Hard Times is a novel of social […] ",
 "format": "Hardcover",
 "rating": 3
}
```

Next, add `genres`, `language`, and `rating` to the list of `filterableAttributes`:

You have now configured your index to use these attributes as filters.

## Use facets in a search query

Make a search query setting the `facets` search parameter:

The response returns all books matching the query. It also returns two fields you can use to create a faceted search interface, `facetDistribution` and `facetStats`:

```json
{
 "hits": [
 …
 ],
 …
 "facetDistribution": {
 "genres": {
 "Classics": 6,
 …
 },
 "language": {
 "English": 6,
 "French": 1,
 "Spanish": 1
 },
 "rating": {
 "2.5": 1,
 …
 }
 },
 "facetStats": {
 "rating": {
 "min": 2.5,
 "max": 4.7
 }
 }
}
```

`facetDistribution` lists all facets present in your search results, along with the number of documents returned for each facet.

`facetStats` contains the highest and lowest values for all facets containing numeric values.

### Sorting facet values

By default, all facet values are sorted in ascending alphanumeric order. You can change this using the `sortFacetValuesBy` property of the [`faceting` index settings](/reference/api/settings#faceting):

The above code sample sorts the `genres` facet by descending value count.

Repeating the previous query using the new settings will result in a different order in `facetsDistribution`:

```json
{
 …
 "facetDistribution": {
 "genres": {
 "Fiction": 8,
 "Literature": 7,
 "Classics": 6,
 "Novel": 2,
 "Horror": 2,
 "Fantasy": 2,
 "Victorian": 2,
 "Vampires": 1,
 "Tragedy": 1,
 "Satire": 1,
 "Romance": 1,
 "Historical Fiction": 1,
 "Coming-of-Age": 1,
 "Comedy": 1
 },
 …
 }
}
```

## Searching facet values

You can also search for facet values with the [facet search endpoint](/reference/api/facet_search):

The following code sample searches the `genres` facet for values starting with `c`:

The response contains a `facetHits` array listing all matching facets, together with the total number of documents that include that facet:

```json
{
 …
 "facetHits": [
 {
 "value": "Children's Literature",
 "count": 1
 },
 {
 "value": "Classics",
 "count": 6
 },
 {
 "value": "Comedy",
 "count": 2
 },
 {
 "value": "Coming-of-Age",
 "count": 1
 }
 ],
 "facetQuery": "c",
 …
}
```

You can further refine results using the `q`, `filter`, and `matchingStrategy` parameters. [Learn more about them in the API reference.](/reference/api/facet_search)

---

## Sort search results

import CodeSamplesSortingGuideUpdateSortableAttributes1 from '/snippets/samples/code_samples_sorting_guide_update_sortable_attributes_1.mdx';
import CodeSamplesSortingGuideUpdateRankingRules1 from '/snippets/samples/code_samples_sorting_guide_update_ranking_rules_1.mdx';
import CodeSamplesSortingGuideSortParameter1 from '/snippets/samples/code_samples_sorting_guide_sort_parameter_1.mdx';
import CodeSamplesSortingGuideSortParameter2 from '/snippets/samples/code_samples_sorting_guide_sort_parameter_2.mdx';
import CodeSamplesSortingGuideSortNested1 from '/snippets/samples/code_samples_sorting_guide_sort_nested_1.mdx';

By default, Meilisearch focuses on ordering results according to their relevancy. You can alter this sorting behavior so users can decide at search time what type of results they want to see first.

This can be useful in many situations, such as when a user wants to see the cheapest products available in a webshop.

Sorting at search time can be particularly effective when combined with [placeholder searches](/reference/api/search#placeholder-search).

## Configure Meilisearch for sorting at search time

To allow your users to sort results at search time you must:

1. Decide which attributes you want to use for sorting
2. Add those attributes to the `sortableAttributes` index setting
3. Update Meilisearch's [ranking rules](/learn/relevancy/relevancy) (optional)

Meilisearch sorts strings in lexicographic order based on their byte values. e.g., `á`, which has a value of 225, will be sorted after `z`, which has a value of 122.

Uppercase letters are sorted as if they were lowercase. They will still appear uppercase in search results.

### Add attributes to `sortableAttributes`

Meilisearch allows you to sort results based on document fields. Only fields containing numbers, strings, arrays of numeric values, and arrays of string values can be used for sorting.

After you have decided which fields you will allow your users to sort on, you must add their attributes to the [`sortableAttributes` index setting](/reference/api/settings#sortable-attributes).

If a field has values of different types across documents, Meilisearch will give precedence to numbers over strings. This means documents with numeric field values will be ranked higher than those with string values.

This can lead to unexpected behavior when sorting. For optimal user experience, only sort based on fields containing the same type of value.

#### Example

Suppose you have collection of books containing the following fields:

```json
[
 {
 "id": 1,
 "title": "Solaris",
 "author": "Stanislaw Lem",
 "genres": [
 "science fiction"
 ],
 "rating": {
 "critics": 95,
 "users": 87
 },
 "price": 5.00
 },
 …
]
```

If you are using this dataset in a webshop, you might want to allow your users to sort on `author` and `price`:

### Customize ranking rule order (optional)

When users sort results at search time, [Meilisearch's ranking rules](/learn/relevancy/relevancy) are set up so the top matches emphasize relevant results over sorting order. You might need to alter this behavior depending on your application's needs.

This is the default configuration of Meilisearch's ranking rules:

```json
[
 "words",
 "typo",
 "proximity",
 "attribute",
 "sort",
 "exactness"
]
```

`"sort"` is in fifth place. This means it acts as a tie-breaker rule: Meilisearch will first place results closely matching search terms at the top of the returned documents list and only then will apply the `"sort"` parameters as requested by the user. In other words, by default Meilisearch provides a very relevant sorting.

Placing `"sort"` ranking rule higher in the list will emphasize exhaustive sorting over relevant sorting: your results will more closely follow the sorting order your user chose, but will not be as relevant.

Sorting applies equally to all documents. Meilisearch does not offer native support for promoting, pinning, and boosting specific documents so they are displayed more prominently than other search results. Consult these Meilisearch blog articles for workarounds on [implementing promoted search results with React InstantSearch](https://blog.meilisearch.com/promoted-search-results-with-react-instantsearch) and [document boosting](https://blog.meilisearch.com/document-boosting).

#### Example

If your users care more about finding cheaper books than they care about finding specific matches to their queries, you can place `sort` much higher in the ranking rules:

## Sort results at search time

After configuring `sortableAttributes`, you can use the [`sort` search parameter](/reference/api/search#sort) to control the sorting order of your search results.

`sort` expects a list of attributes that have been added to the `sortableAttributes` list.

Attributes must be given as `attribute:sorting_order`. In other words, each attribute must be followed by a colon (`:`) and a sorting order: either ascending (`asc`) or descending (`desc`).

When using the POST route, `sort` expects an array of strings:

```json
"sort": [
 "price:asc",
 "author:desc"
]
```

When using the GET route, `sort` expects a comma-separated string:

```
sort="price:desc,author:asc"
```

The order of `sort` values matter: the higher an attribute is in the search parameter value, the more Meilisearch will prioritize it over attributes placed lower. In our example, if multiple documents have the same value for `price`, Meilisearch will decide the order between these similarly-priced documents based on their `author`.

### Example

Suppose you are searching for books in a webshop and want to see the cheapest science fiction titles. This query searches for `"science fiction"` books sorted from cheapest to most expensive:

With our example dataset, the results look like this:

```json
[
 {
 "id": 1,
 "title": "Solaris",
 "author": "Stanislaw Lem",
 "genres": [
 "science fiction"
 ],
 "rating": {
 "critics": 95,
 "users": 87
 },
 "price": 5.00
 },
 {
 "id": 2,
 "title": "The Parable of the Sower",
 "author": "Octavia E. Butler",
 "genres": [
 "science fiction"
 ],
 "rating": {
 "critics": 90,
 "users": 92
 },
 "price": 10.00
 }
]
```

It is common to search books based on an author's name. `sort` can help grouping results from the same author. This query would only return books matching the query term `"butler"` and group results according to their authors:

```json
[
 {
 "id": 2,
 "title": "The Parable of the Sower",
 "author": "Octavia E. Butler",
 "genres": [
 "science fiction"
 ],
 "rating": {
 "critics": 90,
 "users": 92
 },
 "price": 10.00
 },
 {
 "id": 5,
 "title": "Wild Seed",
 "author": "Octavia E. Butler",
 "genres": [
 "fantasy"
 ],
 "rating": {
 "critics": 84,
 "users": 80
 },
 "price": 5.00
 },
 {
 "id": 4,
 "title": "Gender Trouble",
 "author": "Judith Butler",
 "genres": [
 "feminism",
 "philosophy"
 ],
 "rating": {
 "critics": 86,
 "users": 73
 },
 "price": 10.00
 }
]
```

### Sort by nested fields

Use dot notation to sort results based on a document's nested fields. The following query sorts returned documents by their user review scores:

## Sorting and custom ranking rules

There is a lot of overlap between sorting and configuring [custom ranking rules](/learn/relevancy/custom_ranking_rules), as both can greatly influence which results a user will see first.

Sorting is most useful when you want your users to be able to alter the order of returned results at query time. e.g., webshop users might want to order results by price depending on what they are searching and to change whether they see the most expensive or the cheapest products first.

Custom ranking rules, instead, establish a default sorting rule i.e. enforced in every search. This approach can be useful when you want to promote certain results above all others, regardless of a user's preferences. e.g., you might want a webshop to always feature discounted products first, no matter what a user is searching for.

## Example application

Take a look at our demos for examples of how to implement sorting:

- **Ecommerce demo**: [preview](https://ecommerce.meilisearch.com/) • [GitHub repository](https://github.com/meilisearch/ecommerce-demo/)
- **CRM SaaS demo**: [preview](https://saas.meilisearch.com/) • [GitHub repository](https://github.com/meilisearch/saas-demo/)

---

## Filtering and sorting by date

import CodeSamplesDateGuideIndex1 from '/snippets/samples/code_samples_date_guide_index_1.mdx';
import CodeSamplesDateGuideFilterableAttributes1 from '/snippets/samples/code_samples_date_guide_filterable_attributes_1.mdx';
import CodeSamplesDateGuideFilter1 from '/snippets/samples/code_samples_date_guide_filter_1.mdx';
import CodeSamplesDateGuideSortableAttributes1 from '/snippets/samples/code_samples_date_guide_sortable_attributes_1.mdx';
import CodeSamplesDateGuideSort1 from '/snippets/samples/code_samples_date_guide_sort_1.mdx';

In this guide, you will learn about Meilisearch's approach to date and time values, how to prepare your dataset for indexing, and how to chronologically sort and filter search results.

## Preparing your documents

To filter and sort search results chronologically, your documents must have at least one field containing a [UNIX timestamp](https://kb.narrative.io/what-is-unix-time). You may also use a string with a date in a format that can be sorted lexicographically, such as `"2025-01-13"`.

As an example, consider a database of video games. In this dataset, the release year is formatted as a timestamp:

```json
[
 {
 "id": 0,
 "title": "Return of the Obra Dinn",
 "genre": "adventure",
 "release_timestamp": 1538949600
 },
 {
 "id": 1,
 "title": "The Excavation of Hob's Barrow",
 "genre": "adventure",
 "release_timestamp": 1664316000
 },
 {
 "id": 2,
 "title": "Bayonetta 2",
 "genre": "action",
 "release_timestamp": 1411164000
 }
]
```

Once all documents in your dataset have a date field, [index your data](/reference/api/documents#add-or-replace-documents) as usual. The example below adds a <a id="downloadVideogames" href="/assets/datasets/videogames.json" download="videogames.json">videogame dataset</a> to a `games` index:

## Filtering by date

To filter search results based on their timestamp, add your document's timestamp field to the list of [`filterableAttributes`](/reference/api/settings#update-filterable-attributes):

Once you have configured `filterableAttributes`, you can filter search results by date. The following query only returns games released between 2018 and 2022:

## Sorting by date

To sort search results chronologically, add your document's timestamp field to the list of [`sortableAttributes`](/reference/api/settings#update-sortable-attributes):

Once you have configured `sortableAttributes`, you can sort your search results based on their timestamp. The following query returns all games sorted from most recent to oldest:

---

## Getting started with Cloud

This tutorial walks you through setting up [Cloud](https://meilisearch.com/cloud), creating a project and an index, adding documents to it, and performing your first search with the default web interface.

You need a Cloud account to follow along. If you don't have one, register for a 14-day free trial account at [https://cloud.meilisearch.com/register](https://cloud.meilisearch.com/register?utm_campaign=oss&utm_source=docs&utm_medium=cloud-quick-start).

<iframe
width="560"
height="315"
src="https://www.youtube.com/embed/KK2rV7i4IdI?si=F2DuOvzr7Du2jorz"
title="Getting started with Cloud"
frameborder="0"
allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
allowfullscreen
></iframe>

## Creating a project

To use Cloud, you must first create a project. Projects act as containers for indexes, tasks, billing, and other information related to Cloud.

Click the "New project" button on the top menu. If you have a free trial account and this is your first project, the button will read "Start free trial" instead:

 <img src="/assets/images/cloud-getting-started/1-new-project.png" alt="The Cloud menu, featuring the 'New Project' button" />

Name your project `meilisearch-quick-start` and select the region closest to you, then click on "Create project":

 <img src="/assets/images/cloud-getting-started/2-create-project.png" alt="A modal window with two mandatory fields: 'Project name' and 'Select a region'" />

If you are not using a free trial account, you must also choose a billing plan based on the size of your dataset and number of searches per month:

 <img src="/assets/images/cloud-getting-started/3-project-billing.png" alt="A variation of the previous modal window with an extra mandatory field: 'Select a plan'. There are a few billing plan options" />

Creating your project might take a few minutes. Check the project list to follow its status. Once the project is ready, click on its name to go to the project overview page:

 <img src="/assets/images/cloud-getting-started/4-project-list.png" alt="Cloud's main list of projects. It features only one project, 'meilisearch-quick-start', and shows information such as API keys, URL, and number of monthly searches" />

## Creating an index and adding documents

After creating your project, you must index the data you want to search. Meilisearch stores and processes data you add to it in indexes. A single project may contain multiple indexes.

First, click on the indexes tab in the project page menu:

 <img src="/assets/images/cloud-getting-started/5-project-page-menu-indexes.png" alt="The project overview page, featuring a secondary menu with several links. A red arrow points at a menu item: 'Indexes'" />

This leads you to the index listing. Click on "New index":

 <img src="/assets/images/cloud-getting-started/6-index-list-empty.png" alt="An empty list of indexes in this project with a button on the upper right corner" />

Write `movies` in the name field and click on "Create Index":

 <img src="/assets/images/cloud-getting-started/7-create-index.png" alt="A modal window with one mandatory field: 'Index name'" />

The final step in creating an index is to add data to it. Choose "File upload":

 <img src="/assets/images/cloud-getting-started/8-file-upload.png" alt="Another modal window with three options. A red arrow points at the chosen option, 'File upload'" />

Cloud will ask you for your dataset. To follow along, use this <a href="/assets/datasets/movies.json" download="movies.json">list of movies</a>. Download the file to your computer, drag and drop it into the indicated area, then click on "Import documents":

 <img src="/assets/images/cloud-getting-started/9-data-import.png" alt="Another modal window with a large drag-and-drop area. It indicates a file named 'movies.json' will be uploaded" />

Cloud will index your documents. This may take a moment. Click on "See index list" and wait. Once it is done, click on "Settings" to visit the index overview:

 <img src="/assets/images/cloud-getting-started/10-index-list-filled.png" alt="A list of all indexes in this project. It shows a single index, `movies`, and indicates it contains over 30,000 documents" />

## Searching

With all data uploaded and processed, the last step is to run a few test searches to confirm Meilisearch is running as expected.

Click on the project name on the breadcrumb menu to return to the project overview:

 <img src="/assets/images/cloud-getting-started/11-index-list-breadcrumb.png" alt="The index list page. A red arrow points at the breadcrumb menu" />

Cloud comes with a search preview interface. Click on "Search preview" to access it:

 <img src="/assets/images/cloud-getting-started/12-project-page-url.png" alt="The project overview page. A red arrow points at a menu item named 'Search preview'" />

Finally, try searching for a few movies, like "Solaris":

 <img src="/assets/images/cloud-getting-started/13-search-preview.png" alt="The search preview interface, with 'solaris' written in the search bar" />

If you can see the results coming in as you type, congratulations: you now know all the basic steps to using Cloud.

## What's next

This tutorial taught you how to use Cloud's interface to create a project, add an index to it, and use the search preview interface.

In most real-life settings, you will be creating your own search interface and retrieving results through Meilisearch's API. To learn how to add documents and search using the command-line or an SDK in your preferred language, check out the [Meilisearch quick start](/learn/self_hosted/getting_started_with_self_hosted_meilisearch).

---

## Documents

A document is an object composed of one or more fields. Each field consists of an **attribute** and its associated **value**. Documents function as containers for organizing data and are the basic building blocks of a Meilisearch database. To search for a document, you must first add it to an [index](/learn/getting_started/indexes).

Nothing will be shared between two indexes if they contain the exact same document. Instead, both documents will be treated as different documents. Depending on the [index's settings](/reference/api/settings), the documents might have different sizes.

## Structure

 <img src="/assets/images/document_structure.svg" alt="Diagram illustration Meilisearch's document structure" />

### Important terms

- **Document**: an object which contains data in the form of one or more fields
- **[Field](#fields)**: a set of two data items that are linked together: an attribute and a value
- **Attribute**: the first part of a field. Acts as a name or description for its associated value
- **Value**: the second part of a field, consisting of data of any valid JSON type
- **[Primary Field](#primary-field)**: a special field i.e. mandatory in all documents. It contains the primary key and document identifier

## Fields

A **field** is a set of two data items linked together: an attribute and a value. Documents are made up of fields.

An **attribute** is a case-sensitive string that functions as a field's name and allows you to store, access, and describe data.

That data is the field's **value**. Every field has a data type dictated by its value. Every value must be a valid [JSON data type](https://www.w3schools.com/js/js_json_datatypes.asp).

If the value is a string, it **[can contain at most 65535 positions](/learn/resources/known_limitations#maximum-number-of-words-per-attribute)**. Words exceeding the 65535 position limit will be ignored.

If a field contains an object, Meilisearch flattens it during indexing using dot notation and brings the object's keys and values to the root level of the document itself. This flattened object is only an intermediary representation—you will get the original structure upon search. You can read more about this in our [dedicated guide](/learn/engine/datatypes#objects).

With [ranking rules](/learn/relevancy/ranking_rules), you can decide which fields are more relevant than others. e.g., you may decide recent movies should be more relevant than older ones. You can also designate certain fields as displayed or searchable.

Some features require Meilisearch to reserve attributes. e.g., to use [geosearch functionality](/learn/filtering_and_sorting/geosearch) your documents must include a `_geo` field.

Reserved attributes are always prefixed with an underscore (`_`).

### Displayed and searchable fields

By default, all fields in a document are both displayed and searchable. Displayed fields are contained in each matching document, while searchable fields are searched for matching query words.

You can modify this behavior using the [update settings endpoint](/reference/api/settings#update-settings), or the respective update endpoints for [displayed attributes](/reference/api/settings#update-displayed-attributes), and [searchable attributes](/reference/api/settings#update-searchable-attributes) so that a field is:

- Searchable but not displayed
- Displayed but not searchable
- Neither displayed nor searchable

In the latter case, the field will be completely ignored during search. However, it will still be [stored](/learn/relevancy/displayed_searchable_attributes#data-storing) in the document.

To learn more, refer to our [displayed and searchable attributes guide](/learn/relevancy/displayed_searchable_attributes).

## Primary field

The primary field is a special field that must be present in all documents. Its attribute is the [primary key](/learn/getting_started/primary_key#primary-field) and its value is the [document id](/learn/getting_started/primary_key#document-id). If you try to [index a document](/learn/self_hosted/getting_started_with_self_hosted_meilisearch#add-documents) that's missing a primary key or possessing the wrong primary key for a given index, it will cause an error and no documents will be added.

To learn more, refer to the [primary key explanation](/learn/getting_started/primary_key).

## Upload

By default, Meilisearch limits the size of all payloads—and therefore document uploads—to 100MB. You can [change the payload size limit](/learn/self_hosted/configure_meilisearch_at_launch#payload-limit-size) at runtime using the `http-payload-size-limit` option.

Meilisearch uses a lot of RAM when indexing documents. Be aware of your [RAM availability](/learn/resources/faq#what-are-the-recommended-requirements-for-hosting-a-meilisearch-instance) as you increase your batch size as this could cause Meilisearch to crash.

When using the [add new documents endpoint](/reference/api/documents#add-or-update-documents), ensure:

- The payload format is correct. There are no extraneous commas, mismatched brackets, missing quotes, etc.
- All documents are sent in an array, even if there is only one document

### Dataset format

Meilisearch accepts datasets in the following formats:

- [JSON](#json)
- [NDJSON](#ndjson)
- [CSV](#csv)

#### JSON

Documents represented as JSON objects are key-value pairs enclosed by curly brackets. As such, [any rule that applies to formatting JSON objects](https://www.w3schools.com/js/js_json_objects.asp) also applies to formatting Meilisearch documents. e.g., an attribute must be a string, while a value must be a valid [JSON data type](https://www.w3schools.com/js/js_json_datatypes.asp).

Meilisearch will only accept JSON documents when it receives the `application/json` content-type header.

As an example, let's say you are creating an index that contains information about movies. A sample document might look like this:

```json
{
 "id": 1564,
 "title": "Kung Fu Panda",
 "genres": "Children's Animation",
 "release-year": 2008,
 "cast": [
 { "Jack Black": "Po" },
 { "Jackie Chan": "Monkey" }
 ]
}
```

In the above example:

- `"id"`, `"title"`, `"genres"`, `"release-year"`, and `"cast"` are attributes
- Each attribute is associated with a value, e.g., `"Kung Fu Panda"` is the value of `"title"`
- The document contains a field with the primary key attribute and a unique document id as its value: `"id": "1564"`

#### NDJSON

NDJSON or jsonlines objects consist of individual lines where each individual line is valid JSON text and each line is delimited with a newline character. Any [rules that apply to formatting NDJSON](https://github.com/ndjson/ndjson-spec) also apply to Meilisearch documents.

Meilisearch will only accept NDJSON documents when it receives the `application/x-ndjson` content-type header.

Compared to JSON, NDJSON has better writing performance and is less CPU and memory intensive. It is easier to validate and, unlike CSV, can handle nested structures.

The above JSON document would look like this in NDJSON:

```json
{ "id": 1564, "title": "Kung Fu Panda", "genres": "Children's Animation", "release-year": 2008, "cast": [{ "Jack Black": "Po" }, { "Jackie Chan": "Monkey" }] }
```

#### CSV

CSV files express data as a sequence of values separated by a delimiter character. Meilisearch accepts `string`, `boolean`, and `number` data types for CSV documents. If you don't specify the data type for an attribute, it will default to `string`. Empty fields such as `,,` and `, ,` will be considered `null`.

By default, Meilisearch uses a single comma (`,`) as the delimiter. Use the `csvDelimiter` query parameter with the [add or update documents](/reference/api/documents#add-or-update-documents) or [add or replace documents](/reference/api/documents#add-or-replace-documents) endpoints to set a different character. Any [rules that apply to formatting CSV](https://datatracker.ietf.org/doc/html/rfc4180) also apply to Meilisearch documents.

Meilisearch will only accept CSV documents when it receives the `text/csv` content-type header.

Compared to JSON, CSV has better writing performance and is less CPU and memory intensive.

The above JSON document would look like this in CSV:

```csv
 "id:number","title:string","genres:string","release-year:number"
 "1564","Kung Fu Panda","Children's Animation","2008"
```

Since CSV does not support arrays or nested objects, `cast` cannot be converted to CSV.

### Auto-batching

Auto-batching combines similar operations in the same index into a single batch, then processes them together. This significantly speeds up the indexing process.

Tasks within the same batch share the same values for `startedAt`, `finishedAt`, and `duration`.

If a task fails due to an invalid document, it will be removed from the batch. The rest of the batch will still process normally. If an [`internal`](/reference/errors/overview#errors) error occurs, the whole batch will fail and all tasks within it will share the same `error` object.

#### Auto-batching and task cancellation

If the task you're canceling is part of a batch, Meilisearch interrupts the whole process, discards all progress, and cancels that task. Then, it automatically creates a new batch without the canceled task and immediately starts processing it.

---

## Indexes

An index is a group of documents with associated settings. It is comparable to a table in `SQL` or a collection in MongoDB.

An index is defined by a `uid` and contains the following information:

- One [primary key](#primary-key)
- Customizable [settings](#index-settings)
- An arbitrary number of documents

#### Example

Suppose you manage a database that contains information about movies, similar to [IMDb](https://imdb.com/). You would probably want to keep multiple types of documents, such as movies, TV shows, actors, directors, and more. Each of these categories would be represented by an index in Meilisearch.

Using an index's settings, you can customize search behavior for that index. e.g., a `movies` index might contain documents with fields like `movie_id`, `title`, `genre`, `overview`, and `release_date`. Using settings, you could make a movie's `title` have a bigger impact on search results than its `overview`, or make the `movie_id` field non-searchable.

One index's settings do not impact other indexes. e.g., you could use a different list of synonyms for your `movies` index than for your `costumes` index, even if they're on the same server.

## Index creation

### Implicit index creation

If you try to add documents or settings to an index that does not already exist, Meilisearch will automatically create it for you.

### Explicit index creation

You can explicitly create an index using the [create index endpoint](/reference/api/indexes#create-an-index). Once created, you can add documents using the [add documents endpoint](/reference/api/documents#add-or-update-documents).

While implicit index creation is more convenient, requiring only a single API request, **explicit index creation is considered safer for production**. This is because implicit index creation bundles multiple actions into a single task. If one action completes successfully while the other fails, the problem can be difficult to diagnose.

## Index UID

The `uid` is the **unique identifier** of an index. It is set when creating the index and must be an integer or string containing only alphanumeric characters `a-z A-Z 0-9`, hyphens `-` and underscores `_`.

```json
{
 "uid": "movies",
 "createdAt": "2019-11-20T09:40:33.711324Z",
 "updatedAt": "2019-11-20T10:16:42.761858Z"
}
```

You can change an index's `uid` using the [`/indexes` API route](/reference/api/indexes#update-an-index).

## Primary key

Every index has a primary key: a required attribute that must be present in all documents in the index. Each document must have a unique value associated with this attribute.

The primary key serves to identify each document, such that two documents in an index can never be completely identical. If you add two documents with the same value for the primary key, they will be treated as the same document: one will overwrite the other. If you try adding documents, and even a single one is missing the primary key, none of the documents will be stored.

You can set the primary key for an index or let it be inferred by Meilisearch. Read more about [setting the primary key](/learn/getting_started/primary_key#setting-the-primary-key).

[Learn more about the primary field](/learn/getting_started/primary_key)

## Index settings

Index settings can be thought of as a JSON object containing many different options for customizing search behavior.

To change index settings, use the [update settings endpoint](/reference/api/settings#update-settings) or any of the child routes.

### Displayed and searchable attributes

By default, every document field is searchable and displayed in response to search queries. However, you can choose to set some fields as non-searchable, non-displayed, or both.

You can update these field attributes using the [update settings endpoint](/reference/api/settings#update-settings), or the respective endpoints for [displayed attributes](/reference/api/settings#update-displayed-attributes) and [searchable attributes](/reference/api/settings#update-searchable-attributes).

[Learn more about displayed and searchable attributes.](/learn/relevancy/displayed_searchable_attributes)

### Distinct attribute

If your dataset contains multiple similar documents, you may want to return only one on search. Suppose you have numerous black jackets in different sizes in your `costumes` index. Setting `costume_name` as the distinct attribute will mean Meilisearch will not return more than one black jacket with the same `costume_name`.

Designate the distinct attribute using the [update settings endpoint](/reference/api/settings#update-settings) or the [update distinct attribute endpoint](/reference/api/settings#update-distinct-attribute). **You can only set one field as the distinct attribute per index.**

[Learn more about distinct attributes.](/learn/relevancy/distinct_attribute)

### Faceting

Facets are a specific use-case of filters in Meilisearch: whether something is a facet or filter depends on your UI and UX design. Like filters, you need to add your facets to [`filterableAttributes`](/reference/api/settings#update-filterable-attributes), then make a search query using the [`filter` search parameter](/reference/api/search#filter).

By default, Meilisearch returns `100` facet values for each faceted field. You can change this using the [update settings endpoint](/reference/api/settings#update-settings) or the [update faceting settings endpoint](/reference/api/settings#update-faceting-settings).

[Learn more about faceting.](/learn/filtering_and_sorting/search_with_facet_filters)

### Filterable attributes

Filtering allows you to refine your search based on different categories. e.g., you could search for all movies of a certain `genre`: `Science Fiction`, with a `rating` above `8`.

Before filtering on any document attribute, you must add it to `filterableAttributes` using the [update settings endpoint](/reference/api/settings#update-settings) or the [update filterable attributes endpoint](/reference/api/settings#update-filterable-attributes). Then, make a search query using the [`filter` search parameter](/reference/api/search#filter).

[Learn more about filtering.](/learn/filtering_and_sorting/filter_search_results)

### Pagination

To protect your database from malicious scraping, Meilisearch only returns up to `1000` results for a search query. You can change this limit using the [update settings endpoint](/reference/api/settings#update-settings) or the [update pagination settings endpoint](/reference/api/settings#update-pagination-settings).

[Learn more about pagination.](/guides/front_end/pagination)

### Ranking rules

Meilisearch uses ranking rules to sort matching documents so that the most relevant documents appear at the top. All indexes are created with the same built-in ranking rules executed in default order. The order of these rules matters: the first rule has the most impact, and the last rule has the least.

You can alter this order or define custom ranking rules to return certain results first. This can be done using the [update settings endpoint](/reference/api/settings#update-settings) or the [update ranking rules endpoint](/reference/api/settings#update-ranking-rules).

[Learn more about ranking rules.](/learn/relevancy/relevancy)

### Sortable attributes

By default, Meilisearch orders results according to their relevancy. You can alter this sorting behavior to show certain results first.

Add the attributes you'd like to sort by to `sortableAttributes` using the [update settings endpoint](/reference/api/settings#update-settings) or the [update sortable attributes endpoint](/reference/api/settings#update-sortable-attributes). You can then use the [`sort` search parameter](/reference/api/search#sort) to sort your results in ascending or descending order.

[Learn more about sorting.](/learn/filtering_and_sorting/sort_search_results)

### Stop words

Your dataset may contain words you want to ignore during search because, e.g., they don't add semantic value or occur too frequently (for instance, `the` or `of` in English). You can add these words to the [stop words list](/reference/api/settings#stop-words) and Meilisearch will ignore them during search.

Change your index's stop words list using the [update settings endpoint](/reference/api/settings#update-settings) or the [update stop words endpoint](/reference/api/settings#update-stop-words). In addition to improving relevancy, designating common words as stop words greatly improves performance.

[Learn more about stop words.](/reference/api/settings#stop-words)

### Synonyms

Your dataset may contain words with similar meanings. For these, you can define a list of synonyms: words that will be treated as the same or similar for search purposes. Words set as synonyms won't always return the same results due to factors like typos and splitting the query.

Since synonyms are defined for a given index, they won't apply to any other index on the same Meilisearch instance. You can create your list of synonyms using the [update settings endpoint](/reference/api/settings#update-settings) or the [update synonyms endpoint](/reference/api/settings#update-synonyms).

[Learn more about synonyms.](/learn/relevancy/synonyms)

### Typo tolerance

Typo tolerance is a built-in feature that helps you find relevant results even when your search queries contain spelling mistakes or typos, e.g., typing `chickne` instead of `chicken`. This setting allows you to do the following for your index:

- Enable or disable typo tolerance
- Configure the minimum word size for typos
- Disable typos on specific words
- Disable typos on specific document attributes

You can update the typo tolerance settings using the [update settings endpoint](/reference/api/settings#update-settings) or the [update typo tolerance endpoint](/reference/api/settings#update-typo-tolerance-settings).

[Learn more about typo tolerance.](/learn/relevancy/typo_tolerance_settings)

## Swapping indexes

Suppose you have an index in production, `movies`, where your users are currently making search requests. You want to deploy a new version of `movies` with different settings, but updating it normally could cause downtime for your users. This problem can be solved using index swapping.

To use index swapping, you would create a second index, `movies_new`, containing all the changes you want to make to `movies`.

This means that the documents, settings, and task history of `movies` will be swapped with the documents, settings, and task history of `movies_new` **without any downtime for the search clients**. The task history of `enqueued` tasks is not modified.

Once swapped, your users will still be making search requests to the `movies` index but it will contain the data of `movies_new`. You can delete `movies_new` after the swap or keep it in case something goes wrong and you want to swap back.

Swapping indexes is an atomic transaction: **either all indexes are successfully swapped, or none are**.

For more information, see the [swap indexes endpoint](/reference/api/indexes#swap-indexes).

---

## Primary key

import CodeSamplesPrimaryFieldGuideCreateIndexPrimaryKey from '/snippets/samples/code_samples_primary_field_guide_create_index_primary_key.mdx';
import CodeSamplesPrimaryFieldGuideAddDocumentPrimaryKey from '/snippets/samples/code_samples_primary_field_guide_add_document_primary_key.mdx';
import CodeSamplesPrimaryFieldGuideUpdateDocumentPrimaryKey from '/snippets/samples/code_samples_primary_field_guide_update_document_primary_key.mdx';

## Primary field

An [index](/learn/getting_started/indexes) in Meilisearch is a collection of [documents](/learn/getting_started/documents). Documents are composed of fields, each field containing an attribute and a value.

The primary field is a special field that must be present in all documents. Its attribute is the **[primary key](#primary-key-1)** and its value is the **[document id](#document-id)**. It uniquely identifies each document in an index, ensuring that **it is impossible to have two exactly identical documents** present in the same index.

### Example

Suppose we have an index of books. Each document contains a number of fields with data on the book's `author`, `title`, and `price`. More importantly, each document contains a **primary field** consisting of the index's **primary key** `id` and a **unique id**.

```json
[
 {
 "id": 1,
 "title": "Diary of a Wimpy Kid: Rodrick Rules",
 "author": "Jeff Kinney",
 "genres": ["comedy","humor"],
 "price": 5.00
 },
 {
 "id": 2,
 "title": "Black Leopard, Red Wolf",
 "author": "Marlon James",
 "genres": ["fantasy","drama"],
 "price": 5.00
 }
]
```

Aside from the primary key, **documents in the same index are not required to share attributes**. A book in this dataset could be missing the `title` or `genre` attribute and still be successfully indexed by Meilisearch, provided it has the `id` attribute.

### Primary key

The primary key is the attribute of the primary field.

Every index has a primary key, an attribute that must be shared across all documents in that index. If you attempt to add documents to an index and even a single one is missing the primary key, **none of the documents will be stored.**

#### Example

```json
{
 "id": 1,
 "title": "Diary of a Wimpy Kid",
 "author": "Jeff Kinney",
 "genres": ["comedy","humor"],
 "price": 5.00
 }
```

Each document in the above index is identified by a primary field containing the primary key `id` and a unique document id value.

### Document id

The document id is the value associated with the primary key. It is part of the primary field and acts as a unique identifier for each document in a given index.

Two documents in an index can have the same values for all attributes except the primary key. If two documents in the same index have the same id, then they are treated as the same document and **the preceding document will be overwritten**.

Document addition requests in Meilisearch are atomic. This means that **if the primary field value of even a single document in a batch is incorrectly formatted, an error will occur, and Meilisearch will not index documents in that batch.**

#### Example

Good:

```json
"id": "_Aabc012_"
```

Bad:

```json
"id": "@BI+* ^5h2%"
```

#### Formatting the document id

The document id must be an integer or a string. If the id is a string, it can only contain alphanumeric characters (`a-z`, `A-Z`, `0-9`), hyphens (`-`), and underscores (`_`).

## Setting the primary key

You can set the primary key explicitly or let Meilisearch infer it from your dataset. Whatever your choice, an index can have only one primary key at a time, and the primary key cannot be changed while documents are present in the index.

### Setting the primary key on index creation

When creating an index manually, you can explicitly indicate the primary key you want that index to use.

The code below creates an index called `books` and sets `reference_number` as its primary key:

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "indexCreation",
 "enqueuedAt": "2022-09-20T12:06:24.364352Z"
}
```

### Setting the primary key on document addition

When adding documents to an empty index, you can explicitly set the index's primary key as part of the document addition request.

The code below adds a document to the `books` index and sets `reference_number` as that index's primary key:

**Response:**

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "documentAdditionOrUpdate",
 "enqueuedAt": "2022-09-20T12:08:55.463926Z"
}
```

### Changing your primary key with the update index endpoint

The primary key cannot be changed while documents are present in the index. To change the primary key of an index that already contains documents, you must therefore [delete all documents](/reference/api/documents#delete-all-documents) from that index, [change the primary key](/reference/api/indexes#update-an-index), then [add them](/reference/api/documents#add-or-replace-documents) again.

The code below updates the primary key to `title`:

**Response:**

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "indexUpdate",
 "enqueuedAt": "2022-09-20T12:10:06.444672Z"
}
```

### Meilisearch guesses your primary key

Suppose you add documents to an index without previously setting its primary key. In this case, Meilisearch will automatically look for an attribute ending with the string `id` in a case-insensitive manner (e.g., `uid`, `BookId`, `ID`) in your first document and set it as the index's primary key.

If Meilisearch finds [multiple attributes ending with `id`](#index_primary_key_multiple_candidates_found) or [cannot find a suitable attribute](#index_primary_key_no_candidate_found), it will throw an error. In both cases, the document addition process will be interrupted and no documents will be added to your index.

## Primary key errors

This section covers some primary key errors and how to resolve them.

### `index_primary_key_multiple_candidates_found`

This error occurs when you add documents to an index for the first time and Meilisearch finds multiple attributes ending with `id`. It can be resolved by [manually setting the index's primary key](#setting-the-primary-key-on-document-addition).

```json
{
 "uid": 4,
 "indexUid": "books",
 "status": "failed",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 5,
 "indexedDocuments": 5
 },
 "error": {
 "message": "The primary key inference failed as the engine found 2 fields ending with `id` in their names: 'id' and 'author_id'. Please specify the primary key manually using the `primaryKey` query parameter.",
 "code": "index_primary_key_multiple_candidates_found",
 "type": "invalid_request",
 "link": "https://docs.meilisearch.com/errors#index-primary-key-multiple-candidates-found"
 },
 "duration": "PT0.006002S",
 "enqueuedAt": "2023-01-17T10:44:42.625574Z",
 "startedAt": "2023-01-17T10:44:42.626041Z",
 "finishedAt": "2023-01-17T10:44:42.632043Z"
}
```

### `index_primary_key_no_candidate_found`

This error occurs when you add documents to an index for the first time and none of them have an attribute ending with `id`. It can be resolved by [manually setting the index's primary key](#setting-the-primary-key-on-document-addition), or ensuring that all documents you add possess an `id` attribute.

```json
{
 "uid": 1,
 "indexUid": "books",
 "status": "failed",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 5,
 "indexedDocuments": null
 },
 "error": {
 "message": "The primary key inference failed as the engine did not find any field ending with `id` in its name. Please specify the primary key manually using the `primaryKey` query parameter.",
 "code": "index_primary_key_no_candidate_found",
 "type": "invalid_request",
 "link": "https://docs.meilisearch.com/errors#index-primary-key-no-candidate-found"
 },
 "duration": "PT0.006579S",
 "enqueuedAt": "2023-01-17T10:19:14.464858Z",
 "startedAt": "2023-01-17T10:19:14.465369Z",
 "finishedAt": "2023-01-17T10:19:14.471948Z"
}
```

### `invalid_document_id`

This happens when your document id does not have the correct [format](#formatting-the-document-id). The document id can only be of type integer or string, composed of alphanumeric characters `a-z A-Z 0-9`, hyphens `-`, and underscores `_`.

```json
{
 "uid": 1,
 "indexUid": "books",
 "status": "failed",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 5,
 "indexedDocuments": null
 },
 "error": {
 "message": "Document identifier `1@` is invalid. A document identifier can be of type integer or string, only composed of alphanumeric characters (a-z A-Z 0-9), hyphens (-) and underscores (_).",
 "code": "invalid_document_id",
 "type": "invalid_request",
 "link": "https://docs.meilisearch.com/errors#invalid_document_id"
 },
 "duration": "PT0.009738S",
 "enqueuedAt": "2021-12-30T11:28:59.075065Z",
 "startedAt": "2021-12-30T11:28:59.076144Z",
 "finishedAt": "2021-12-30T11:28:59.084803Z"
}
```

### `missing_document_id`

This error occurs when your index already has a primary key, but one of the documents you are trying to add is missing this attribute.

```json
{
 "uid": 1,
 "indexUid": "books",
 "status": "failed",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 1,
 "indexedDocuments": null
 },
 "error": {
 "message": "Document doesn't have a `id` attribute: `{\"title\":\"Solaris\",\"author\":\"Stanislaw Lem\",\"genres\":[\"science fiction\"],\"price\":5.0.",
 "code": "missing_document_id",
 "type": "invalid_request",
 "link": "https://docs.meilisearch.com/errors#missing_document_id"
 },
 "duration": "PT0.007899S",
 "enqueuedAt": "2021-12-30T11:23:52.304689Z",
 "startedAt": "2021-12-30T11:23:52.307632Z",
 "finishedAt": "2021-12-30T11:23:52.312588Z"
}
```

---

## Search preview

Cloud gives you access to a dedicated search preview interface. This is useful to test search result relevancy when you are tweaking an index's settings.

If you are self-hosting Meilisearch and need a local search interface, access `http://localhost:7700` in your browser. This local preview only allows you to perform plain searches and offers no customization options.

## Accessing and using search preview

Log into your [Cloud](https://cloud.meilisearch.com/login) account, navigate to your project, then click on "Search preview":

 <img src="/assets/images/search_preview/01-search-preview-menu.png" alt="Cloud's project menu with the last option, 'Search preview', selected" />

Select the index you want to search on using the input on the left-hand side:

 <img src="/assets/images/search_preview/02-select-index.png" alt="Cloud's search preview interface, with the index selecting input highlighted" />

Then use the main input to perform plain keyword searches:

 <img src="/assets/images/search_preview/03-basic-search.png" alt="Cloud's search preview interface, with the search input selected and containing a search string" />

When debugging relevancy, you may want to activate the "Ranking score" option. This displays the overall [ranking score](/learn/relevancy/ranking_score) for each result, together with the score for each individual ranking rule:

 <img src="/assets/images/search_preview/04-score.png" alt="The same search preview interface as in the previous image, but with the 'Ranking score' option turned on. Search results are the same, but include the document's ranking score" />

## Configuring search options

Use the menu on the left-hand side to configure [sorting](/learn/filtering_and_sorting/sort_search_results) and [filtering](/learn/filtering_and_sorting/filter_search_results). These require you to first edit your index's sortable and filterable attributes. You may additionally configure any filterable attributes as facets. In this example, "Genres" is one of the configured facets:

 <img src="/assets/images/search_preview/05-sidebar-options.png" alt="The sidebar of the search preview interface, with a handful of options, including 'Sort by', 'AI-powered search', 'Filters', and 'Genres'" />

You can also perform [AI-powered searches](/learn/ai_powered_search/getting_started_with_ai_search) if this functionality has been enabled for your project.

Clicking on "Advanced parameters" gives you access to further customization options, including setting which document fields Meilisearch returns and explicitly declaring the search language:

 <img src="/assets/images/search_preview/06-sidebar-options-advanced.png" alt="The same sidebar as before with the 'Advanced parameters' option highlighted" />

## Exporting search options

You can export the full search query for further testing in other tools and environments. Click on the cloud icon next to "Advanced parameters", then choose to download a JSON file or copy the query to your clipboard:

 <img src="/assets/images/search_preview/07-sidebar-options-export.png" alt="The same sidebar as before with the 'Export' option highlighted" />

---

## What is Meilisearch?

Meilisearch is a **RESTful search API**. It aims to be a **ready-to-go solution** for everyone who wants a **fast and relevant search experience** for their end-users ⚡️🔎

## Cloud

[Cloud](https://www.meilisearch.com/cloud?utm_campaign=oss&utm_source=docs&utm_medium=what-is-meilisearch) is the recommended way of using Meilisearch. Using Cloud greatly simplifies installing, maintaining, and updating Meilisearch. [Get started with a 14-day free trial](https://www.meilisearch.com/cloud?utm_campaign=oss&utm_source=docs&utm_medium=what-is-meilisearch).

## Demo

[![Search bar updating results](/assets/images/movies-demo-dark.gif)](https://where2watch.meilisearch.com/?utm_campaign=oss&utm_source=docs&utm_medium=what-is-meilisearch&utm_content=gif)
_Meilisearch helps you find where to watch a movie at [where2watch.meilisearch.com](https://where2watch.meilisearch.com/?utm_campaign=oss&utm_source=docs&utm_medium=what-is-meilisearch&utm_content=link)._

## Features

- **Blazing fast**: Answers in less than 50 milliseconds
- [AI-powered search](/learn/ai_powered_search/getting_started_with_ai_search): Use the power of AI to make search feel human
- **Search as you type**: Results are updated on each keystroke using [prefix-search](/learn/engine/prefix#prefix-search)
- [Typo tolerance](/learn/relevancy/typo_tolerance_settings): Get relevant matches even when queries contain typos and misspellings
- [Comprehensive language support](/learn/resources/language): Optimized support for **Chinese, Japanese, Hebrew, and languages using the Latin alphabet**
- **Returns the whole document**: The entire document is returned upon search
- **Highly customizable search and indexing**: Customize search behavior to better meet your needs
- [Custom ranking](/learn/relevancy/relevancy): Customize the relevancy of the search engine and the ranking of the search results
- [Filtering](/learn/filtering_and_sorting/filter_search_results) and [faceted search](/learn/filtering_and_sorting/search_with_facet_filters): Enhance user search experience with custom filters and build a faceted search interface in a few lines of code
- [Highlighting](/reference/api/search#highlight-tags): Highlighted search results in documents
- [Stop words](/reference/api/settings#stop-words): Ignore common non-relevant words like `of` or `the`
- [Synonyms](/reference/api/settings#synonyms): Configure synonyms to include more relevant content in your search results
- **RESTful API**: Integrate Meilisearch in your technical stack with our plugins and SDKs
- [Search preview](/learn/getting_started/search_preview): Allows you to test your search settings without implementing a front-end
- [API key management](/learn/security/basic_security): Protect your instance with API keys. Set expiration dates and control access to indexes and endpoints so that your data is always safe
- [Multitenancy and tenant tokens](/learn/security/multitenancy_tenant_tokens): Manage complex multi-user applications. Tenant tokens help you decide which documents each one of your users can search
- [Multi-search](/reference/api/multi_search): Perform multiple search queries on multiple indexes with a single HTTP request
- [Geosearch](/learn/filtering_and_sorting/geosearch): Filter and sort results based on their geographic location
- [Index swapping](/learn/getting_started/indexes#swapping-indexes): Deploy major database updates with zero search downtime

## Philosophy

Our goal is to provide a simple and intuitive experience for both developers and end-users. Ease of use was the primary focus of Meilisearch from its first release, and it continues to drive its development today.

Meilisearch's ease-of-use goes hand-in-hand with ultra relevant search results. Meilisearch **sorts results according to a set of [ranking rules](/learn/relevancy/ranking_rules)**. Our default ranking rules work for most use cases as we developed them by working directly with our users. You can also **configure the [search parameters](/reference/api/search)** to refine your search even further.

Meilisearch should **not be your main data store**. It is a search engine, not a database. Meilisearch should contain only the data you want your users to search through. If you must add data i.e. irrelevant to search, be sure to [make those fields non-searchable](/learn/relevancy/displayed_searchable_attributes#searchable-fields) to improve relevancy and response time.

Meilisearch provides an intuitive search-as-you-type experience with response times under 50 milliseconds, no matter whether you are developing a site or an app. This helps end-users find what they are looking for quickly and efficiently. To make that happen, we are fully committed to the philosophy of [prefix search](/learn/engine/prefix).

## Give it a try

Instead of showing you examples, why not just invite you to test Meilisearch interactively in the **out-of-the-box search preview** we deliver?

There's no need to write a single line of front-end code. All you need to do is follow [this guide](/learn/self_hosted/getting_started_with_self_hosted_meilisearch) to give the search engine a try!

---

## Indexing best practices

In this guide, you will find some of the best practices to index your data efficiently and speed up the indexing process.

## Define searchable attributes

Review your list of [searchable attributes](/learn/relevancy/displayed_searchable_attributes#searchable-fields) and ensure it includes only the fields you want to be checked for query word matches. This improves both relevancy and search speed by removing irrelevant data from your database. It will also keep your disk usage to the necessary minimum.

By default, all document fields are searchable. The fewer fields Meilisearch needs to index, the faster the indexing process.

### Review filterable and sortable attributes

Some document fields are necessary for [filtering](/learn/filtering_and_sorting/filter_search_results) and [sorting](/learn/filtering_and_sorting/sort_search_results) results, but they do not need to be _searchable_. Generally, **numeric and boolean fields** fall into this category. Make sure to review your list of searchable attributes and remove any fields that are only used for filtering or sorting.

## Configure your index before adding documents

When creating a new index, first [configure its settings](/reference/api/settings) and only then add your documents. Whenever you update settings such as [ranking rules](/learn/relevancy/relevancy), Meilisearch will trigger a reindexing of all your documents. This can be a time-consuming process, especially if you have a large dataset. For this reason, it is better to define ranking rules and other settings before indexing your data.

## Optimize document size

Smaller documents are processed faster, so make sure to trim down any unnecessary data from your documents. When a document field is missing from the list of [searchable](/reference/api/settings#searchable-attributes), [filterable](/reference/api/settings#filterable-attributes), [sortable](/reference/api/settings#sortable-attributes), or [displayed](/reference/api/settings#displayed-attributes) attributes, it might be best to remove it from the document. To go further, consider compressing your data using methods such as `br`, `deflate`, or `gzip`. Consult the [supported encoding formats reference](/reference/api/overview#content-encoding).

## Prefer bigger HTTP payloads

A single large HTTP payload is processed more quickly than multiple smaller payloads. e.g., adding the same 100,000 documents in two batches of 50,000 documents will be quicker than adding them in four batches of 25,000 documents. By default, Meilisearch sets the maximum payload size to 100MB, but [you can change this value if necessary](/learn/self_hosted/configure_meilisearch_at_launch#payload-limit-size).

Larger payload consume more RAM. An instance may crash if it requires more memory than is currently available in a machine.

## Keep Meilisearch up-to-date

Make sure to keep your Meilisearch instance up-to-date to benefit from the latest improvements. You can see [a list of all our engine releases on GitHub](https://github.com/meilisearch/meilisearch/releases?q=prerelease%3Afalse).

For more information on how indexing works under the hood, take a look [this blog post about indexing best practices](https://blog.meilisearch.com/best-practices-for-faster-indexing/).

## Do not use Meilisearch as your main database

Meilisearch is optimized for information retrieval was not designed to be your main data container. The more documents you add, the longer will indexing and search take. Only index documents you want to retrieve when searching.

## Create separate indexes for multiple languages

If you have a multilingual dataset, create a separate index for each language.

## Remove I/O operation limits

Ensure there is no limit to I/O operations in your machine. The restrictions imposed by cloud providers such as [AWS's Amazon EBS service](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html#IOcredit) can severely impact indexing performance.

## Consider upgrading to machines with SSDs, more RAM, and multi-threaded processors

If you have followed the previous tips in this guide and are still experiencing slow indexing times, consider upgrading your machine.

Indexing is a memory-intensive and multi-threaded operation. The more memory and processor cores available, the faster Meilisearch will index new documents. When trying to improve indexing speed, using a machine with more processor cores is more effective than increasing RAM.

Due to how Meilisearch works, it is best to avoid HDDs (Hard Disk Drives) as they can easily become performance bottlenecks.

## Enable binary quantization when using AI-powered search

If you are experiencing performance issues when indexing documents for AI-powered search, consider enabling [binary quantization](/reference/api/settings#binaryquantized) for your embedders. Binary quantization compresses vectors by representing each dimension with 1-bit values. This reduces the relevancy of semantic search results, but greatly improves performance.

Binary quantization works best with large datasets containing more than 1M documents and using models with more than 1400 dimensions.

**Activating binary quantization is irreversible.** Once enabled, Meilisearch converts all vectors and discards all vector data that does fit within 1-bit. The only way to recover the vectors' original values is to re-vectorize the whole index in a new embedder.

---

## Handling multilingual datasets

When working with datasets that include content in multiple languages, it’s important to ensure that both documents and queries are processed correctly. This guide explains how to index and search multilingual datasets in Meilisearch, highlighting best practices, useful features, and what to avoid.

## Recommended indexing strategy

### Create a separate index for each language (recommended)

If you have a multilingual dataset, the best practice is to create one index per language.

#### Benefits

- Provides natural sharding of your data by language, making it easier to maintain and scale.

- Lets you apply language-specific settings, such as [stop words](/reference/api/settings#stop-words), and [separators](/reference/api/settings#separator-tokens).

- Simplifies the handling of complex languages like Chinese or Japanese, which require specialized tokenizers.

#### Searching across languages

If you want to allow users to search in more than one language at once, you can:

- Run a [multi-search](/reference/api/multi_search), querying several indexes in parallel.

- Use [federated search](/reference/api/multi_search#federated-multi-search-requests), aggregating results from multiple language indexes into a single response.

### Create a single index for multiple languages

In some cases, you may prefer to keep multiple languages in a **single index**. This approach is generally acceptable for proof of concepts or datasets with fewer than ~1M documents.

#### When it works well

- Suitable for languages that use spaces to separate words and share similar tokenization behavior (e.g., English, French, Italian, Spanish, Portuguese).

- Useful when you want a simple setup without maintaining multiple indexes.

#### Limitations

- Languages with compound words (like German) or diacritics that change meaning (like Swedish), as well as non-space-separated writing systems (like Chinese, or Japanese), work better in their own index since they require specialized [tokenizers](/learn/indexing/tokenization).

- Chinese and Japanese documents should not be mixed in the same field, since distinguishing between them automatically is very difficult. Each of these languages works best in its own dedicated index. However, if fields are strictly separated by language (e.g., title_zh always Chinese, title_ja always Japanese), it is possible to store them in the same index.

- As the number of documents and languages grows, performance and relevancy can decrease, since queries must run across a larger, mixed dataset.

#### Best practices for the single index approach

- Use language-specific field names with a prefix or suffix (e.g., title_fr, title_en, or fr_title).

- Declare these fields as [localized attributes](/reference/api/settings#localized-attributes) so Meilisearch can apply the correct tokenizer to each one.

- This allows you to filter and search by language, even when multiple languages are stored in the same index.

## Language detection and configuration

Accurate language detection is essential for applying the right tokenizer and normalization rules, which directly impact search quality.

By default, Meilisearch automatically detects the language of your documents and queries.

This automatic detection works well in most cases, especially with longer texts. However, results can vary depending on the type of input:

- **Documents**: detection is generally reliable for longer content, but short snippets may produce less accurate results.
- **Queries**: short or partial inputs (such as type-as-you-search) are harder to identify correctly, making explicit configuration more important.

When you explicitly set `localizedAttributes` for documents and `locales` for queries, you **restrict the detection to the languages you’ve declared**.

**Benefits**:

- Meilisearch only chooses between the specified languages (e.g., English vs German).

- Detection is more **reliable and consistent**, reducing mismatches.

For search to work effectively, **queries must be tokenized and normalized in the same way as documents**. If strategies are not aligned, queries may fail to match even when the correct terms exist in the index.

### Aligning document and query tokenization

To keep queries and documents consistent, Meilisearch provides configuration options for both sides. Meilisearch uses the same `locales` configuration concept for both documents and queries: 

- In **documents**, `locales` are declared through `localizedAttributes`. 
- In **queries**, `locales` are passed as a [search parameter]. 

#### Declaring locales for documents

The [`localizedAttributes` setting](/reference/api/settings#localized-attributes) allows you to explicitly define which languages are present in your dataset, and in which fields.

e.g., if your dataset contains multilingual titles, you can declare which attribute belongs to which language:

```json
{
 "id": 1,
 "title_en": "Danube Steamship Company",
 "title_de": "Donaudampfschifffahrtsgesellschaft",
 "title_fr": "Compagnie de navigation à vapeur du Danube"
}
```

```javascript
client.index('INDEX_NAME').updateLocalizedAttributes([
 { attributePatterns: ['*_en'], locales: ['eng'] },
 { attributePatterns: ['*_de'], locales: ['deu'] },
 { attributePatterns: ['*_fr'], locales: ['fra'] }
])
```

#### Specifying locales for queries

When performing searches, you can specify [query locales](/reference/api/search#query-locales) to ensure queries are tokenized with the correct rules.

```javascript
client.index('INDEX_NAME').search('schiff', { locales: ['deu'] })
```

This ensures queries are interpreted with the correct tokenizer and normalization rules, avoiding false mismatches.

## Conclusion

Handling multilingual datasets in Meilisearch requires careful planning of both indexing and querying. 
By choosing the right indexing strategy, and explicitly configuring languages with `localizedAttributes` and `locales`, you ensure that documents and queries are processed consistently.

---

## Optimize indexing performance with batch statistics

# Optimize indexing performance by analyzing batch statistics

Indexing performance can vary significantly depending on your dataset, index settings, and hardware. The [batch object](/reference/api/batches) provides information about the progress of asynchronous indexing operations.

The `progressTrace` field within the batch object offers a detailed breakdown of where time is spent during the indexing process. Use this data to identify bottlenecks and improve indexing speed.

## Understanding the `progressTrace`

`progressTrace` is a hierarchical trace showing each phase of indexing and how long it took.
Each entry follows the structure:

```json
"processing tasks > indexing > extracting word proximity": "33.71s"
```

This means:

- The step occurred during **indexing**.
- The subtask was **extracting word proximity**.
- It took **33.71 seconds**.

Focus on the **longest-running steps** and investigate which index settings or data characteristics influence them.

## Key phases and how to optimize them

### `computing document changes`and `extracting documents` | Description | Optimization | |---|---| | Meilisearch compares incoming documents to existing ones. | No direct optimization possible. Process duration scales with the number and size of incoming documents.| ### `extracting facets` and `merging facet caches` | Description | Optimization | |---|---| | Extracts and merges filterable attributes. | Keep the number of [**filterable attributes**](/reference/api/settings#filterable-attributes) to a minimum. | ### `extracting words` and `merging word caches` | Description | Optimization | |---|---| | Tokenizes text and builds the inverted index. | Ensure the [searchable attributes](/reference/api/settings#searchable-attributes) list only includes the fields you want to be checked for query word matches. | ### `extracting word proximity` and `merging word proximity` | Description | Optimization | |---|---| | Builds data structures for phrase and attribute ranking. | Lower the precision of this operation by setting [proximity precision](/reference/api/settings#proximity-precision) to `byAttribute` | ### `waiting for database writes` | Description | Optimization | |---|---| | Time spent writing data to disk. | No direct optimization possible. Either the disk is too slow or you are writing too much data in a single operation. Avoid HDDs (Hard Disk Drives) | ### `waiting for extractors` | Description | Optimization | |---|---| | Time spent waiting for CPU-bound extraction. | No direct optimization possible. Indicates a CPU bottleneck. Use more cores or scale horizontally with [sharding](/learn/advanced/sharding). | ### `post processing facets > strings bulk` / `numbers bulk` | Description | Optimization | |---|---| | Processes equality or comparison filters. | - Disable unused [**filter features**](/reference/api/settings#features), such as comparison operators on string values. <br /> - Reduce the number of [**sortable attributes**](reference/api/settings#sortable-attributes). | ### `post processing facets > facet search` | Description | Optimization | |---|---| | Builds structures for the [facet search API](/reference/api/facet_search). | If you don’t use the facet search API, [disable it](/reference/api/settings#update-facet-search-settings).| ### Embeddings | Trace key | Description | Optimization | |---|---|---| | `writing embeddings to database` | Time spent saving vector embeddings. | Use embedding vectors with fewer dimensions. <br/>- Consider enabling [binary quantization](/reference/api/settings#binaryquantized). | | `extracting embeddings` | Time spent extracting embeddings from embedding providers' responses. | Reduce the amount of data sent to embeddings provider. <br/>- [Include fewer attributes in `documentTemplate`](/learn/ai_powered_search/document_template_best_practices). <br/>- [Reduce maximum size of the document template](/reference/api/settings#update-embedder-settings). <br/>- [Disabling embedding regeneration on document update](/reference/api/documents#vectors). <br/>- If using a third-party service like OpenAI, upgrade your account to a higher tier.| ### `post processing words > word prefix *` | Description | Optimization | |---|---| | | Builds prefix data for autocomplete. Allows matching documents that begin with a specific query term, instead of only exact matches.| Disable [**prefix search**](/reference/api/settings#prefix-search) (`prefixSearch: disabled`). _This can severely impact search result relevancy._ | ### `post processing words > word fst` | Description | Optimization | |---|---| | Builds the word FST (finite state transducer). | No direct action possible, as FST size reflect the number of different words in the database. Using documents with fewer searchable words may improve operation speed. | ## Example analysis

If you see:

```json
"processing tasks > indexing > post processing facets > facet search": "1763.06s"
```

[Facet searching](/learn/filtering_and_sorting/search_with_facet_filters#searching-facet-values) is raking significant indexing time. If your application doesn’t use facets, disable the feature:

[cURL example omitted]

## Learn more

- [Indexing best practices](/learn/indexing/indexing_best_practices)
- [Impact of RAM and multi-threading on indexing performance
](/learn/indexing/ram_multithreading_performance) 
- [Configuring index settings](/learn/configuration/configuring_index_settings)

---

## Impact of RAM and multi-threading on indexing performance

Adding new documents to an index is a multi-threaded and memory-intensive operation. Meilisearch's indexes are at the core of what makes our search engine fast, relevant, and reliable. This article explains some of the details regarding RAM consumption and multi-threading.

## RAM

By default, our indexer uses the `sysinfo` Rust library to calculate a machine's total memory size. Meilisearch then adapts its behavior so indexing uses a maximum two thirds of available resources. Alternatively, you can use the [`--max-indexing-memory`](/learn/self_hosted/configure_meilisearch_at_launch#max-indexing-memory) instance option to manually control the maximum amount of RAM Meilisearch can consume.

It is important to prevent Meilisearch from using all available memory during indexing. If that happens, there are two negative consequences:

1. Meilisearch may be killed by the OS for over-consuming RAM

2. Search performance may decrease while the indexer is processing an update

Memory overconsumption can still happen in two cases:

1. When letting Meilisearch automatically set the maximum amount of memory used during indexing, `sysinfo` may not be able to calculate the amount of available RAM for certain OSes. Meilisearch still makes an educated estimate and adapts its behavior based on that, but crashes may still happen in this case. [Follow this link for an exhaustive list of OSes supported by `sysinfo`](https://docs.rs/sysinfo/0.20.0/sysinfo/#supported-oses)

2. Lower-end machines might struggle when processing huge datasets. Splitting your data payload into smaller batches can help in this case. [For more information, consult the section below](#memory-crashes)

## Multi-threading

In machines with multi-core processors, the indexer avoids using more than half of the available processing units. e.g., if your machine has twelve cores, the indexer will try to use six of them at most. This ensures Meilisearch is always ready to perform searches, even while you are updating an index.

You can override Meilisearch's default threading limit by using the [`--max-indexing-threads`](/learn/self_hosted/configure_meilisearch_at_launch#max-indexing-threads) instance option. Allowing Meilisearch to use all processor cores for indexing might negatively impact your users' search experience.

Multi-threading is unfortunately not possible in machines with only one processor core.

## Memory crashes

In some cases, the OS will interrupt Meilisearch and stop all its processes. Most of these crashes happen during indexing and are a result of a machine running out of RAM. This means your computer does not have enough memory to process your dataset.

Meilisearch is aware of this issue and actively trying to resolve it. If you are struggling with memory-related crashes, consider:

- Adding new documents in smaller batches
- Increasing your machine's RAM
- [Following indexing best practices](/learn/indexing/indexing_best_practices)

---

## Tokenization

**Tokenization** is the act of taking a sentence or phrase and splitting it into smaller units of language, called tokens. It is the first step of document indexing in the Meilisearch engine, and is a critical factor in the quality of search results.

Breaking sentences into smaller chunks requires understanding where one word ends and another begins, making tokenization a highly complex and language-dependent task. Meilisearch's solution to this problem is a **modular tokenizer** that follows different processes, called **pipelines**, based on the language it detects.

This allows Meilisearch to function in several different languages with zero setup.

## Deep dive: The Meilisearch tokenizer

When you add documents to a Meilisearch index, the tokenization process is handled by an abstract interface called the tokenizer. The tokenizer is responsible for splitting each field by writing system (e.g., Latin alphabet, Chinese hanzi). It then applies the corresponding pipeline to each part of each document field.

We can break down the tokenization process like so:

1. Crawl the document(s), splitting each field by script
2. Go back over the documents part-by-part, running the corresponding tokenization pipeline, if it exists

Pipelines include many language-specific operations. Currently, we have a number of pipelines, including a default pipeline for languages that use whitespace to separate words, and dedicated pipelines for Chinese, Japanese, Hebrew, Thai, and Khmer.

For more details, check out the [tokenizer contribution guide](https://github.com/meilisearch/charabia).

---

## Implement sharding with remote federated search

import { NoticeTag } from '/snippets/notice_tag.mdx';

import CodeSamplesMultiSearchRemoteFederated1 from '/snippets/samples/code_samples_multi_search_remote_federated_1.mdx';

Sharding is the process of splitting an index containing many documents into multiple smaller indexes, often called shards. This horizontal scaling technique is useful when handling large databases. In Meilisearch, the best way to implement a sharding strategy is to use remote federated search.

This guide walks you through activating the `/network` route, configuring the network object, and performing remote federated searches.

Sharding is an Enterprise Edition feature. You are free to use it for evaluation purposes. Please [reach out to us](mailto:sales@meilisearch.com) before using it in production.

## Configuring multiple instances

To minimize issues and limit unexpected behavior, instance, network, and index configuration should be identical for all shards. This guide describes the individual steps you must take on a single instance and assumes you will replicate them across all instances.

## Prerequisites

- Multiple Meilisearch projects (instances) running Meilisearch >=v1.19

## Activate the `/network` endpoint

### Cloud

If you are using Cloud, contact support to enable this feature in your projects.

### Self-hosting

Use the `/experimental-features` route to enable `network`:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "network": true
 }'
```

Meilisearch should respond immediately, confirming the route is now accessible. Repeat this process for all instances.

## Configuring the network object

Next, you must configure the network object. It consists of the following fields:

- `remotes`: defines a list with the required information to access each remote instance
- `self`: specifies which of the configured `remotes` corresponds to the current instance
- `sharding`: whether to use sharding.

### Setting up the list of remotes

Use the `/network` route to configure the `remotes` field of the network object. `remotes` should be an object containing one or more objects. Each one of the nested objects should consist of the name of each instance, associated with its URL and an API key with search permission:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/network' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "remotes": {
 "REMOTE_NAME_1": {
 "url": "INSTANCE_URL_1",
 "searchApiKey": "SEARCH_API_KEY_1"
 },
 "REMOTE_NAME_2": {
 "url": "INSTANCE_URL_2",
 "searchApiKey": "SEARCH_API_KEY_2"
 },
 "REMOTE_NAME_3": {
 "url": "INSTANCE_URL_3",
 "searchApiKey": "SEARCH_API_KEY_3"
 },
 …
 }
 }'
```

Configure the entire set of remote instances in your sharded database, making sure to send the same remotes to each instance.

### Specify the name of the current instance

Now all instances share the same list of remotes, set the `self` field to specify which of the remotes corresponds to the current instance:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/network' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "self": "REMOTE_NAME_1"
 }'
```

Meilisearch processes searches on the remote that corresponds to `self` locally instead of making a remote request.

### Enabling sharding

Finally enable the automatic sharding of documents by Meilisearch on all instances:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/network' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "sharding": true
 }'
```

### Adding or removing an instance

Changing the topology of the network involves moving some documents from an instance to another, depending on your hashing scheme.

As Meilisearch does not provide atomicity across multiple instances, you will need to either:

1. accept search downtime while migrating documents
2. accept some documents will not appear in search results during the migration
3. accept some duplicate documents may appear in search results during the migration

#### Reducing downtime

If your disk space allows, you can reduce the downtime by applying the following algorithm:

1. Create a new temporary index in each remote instance
2. Compute the new instance for each document
3. Send the documents to the temporary index of their new instance
4. Once Meilisearch has copied all documents to their instance of destination, swap the new index with the previously used index
5. Delete the temporary index after the swap
6. Update network configuration and search queries across all instances

## Create indexes

Create the same empty indexes with the same settings on all instances.
Keeping the settings and indexes in sync is important to avoid errors and unexpected behavior, though not strictly required.

## Add documents

Pick a single instance to send all your documents to. Documents will be replicated to the other instances.

Each instance will index the documents they are responsible for and ignore the others.

You *may* send send the same document to multiple instances, the task will be replicated to all instances, and only the instance responsible for the document will index it.

Similarly, you may send any future versions of any document to the instance you picked, and only the correct instance will process that document.

### Updating index settings

Changing settings in a sharded database is not fundamentally different from changing settings on a single Meilisearch instance. If the update enables a feature, such as setting filterable attributes, wait until all changes have been processed before using the `filter` search parameter in a query. Likewise, if an update disables a feature, first remove it from your search requests, then update your settings.

## Perform a search

Send your federated search request containing one query per instance:

If all instances share the same network configuration, you can send the search request to any instance. Having `"remote": "ms-00"` appear in the list of queries on the instance of that name will not cause an actual proxy search thanks to `network.self`.

---

## Differences between multi-search and federated search

This article defines multi-search and federated search and then describes the different uses of each.

## What is multi-search?

Multi-search, also called multi-index search, is a search operation that makes multiple queries at the same time. These queries may target different indexes. Meilisearch then returns a separate list results for each query. Use the `/multi-search` route to perform multi-searches.

Multi-search favors discovery scenarios, where users might not have a clear idea of what they need and searches might have many valid results.

## What is federated search?

Federated search is a type of multi-index search. This operation also makes multiple search requests at the same time, but returns a single list with the most relevant results from all queries. Use the `/multi-search` route and specify a non-null value for `federation` to perform a federated search.

Federated search favors scenarios where users have a clear idea of what they need and expect a single best top result.

## Use cases

Because multi-search groups results by query, it is often useful when the origin and type of document contain information relevant to your users. e.g., a person searching for `shygirl` in a music streaming application is likely to appreciate seeing separate results for matching artists, albums, and individual tracks.

Federated search is a better approach when the source of the information is not relevant to your users. e.g., a person searching for a client's email in a CRM application is unlikely to care whether this email comes from chat logs, support tickets, or other data sources.

---

## Using multi-search to perform a federated search

Meilisearch allows you to make multiple search requests at the same time with the `/multi-search` endpoint. A federated search is a multi-search that returns results from multiple queries in a single list.

In this tutorial you will see how to create separate indexes containing different types of data from a CRM application. You will then perform a query searching all these indexes at the same time to obtain a single list of results.

## Requirements

- A running Meilisearch project
- A command-line console

## Create three indexes

Download the following datasets: <a href="/assets/datasets/crm-chats.json">`crm-chats.json`</a>, <a href="/assets/datasets/crm-profiles.json">`crm-profiles.json`</a>, and <a href="/assets/datasets/crm-tickets.json">`crm-tickets.json`</a> containing data from a fictional CRM application.

Add the datasets to Meilisearch and create three separate indexes, `profiles`, `chats`, and `tickets`:

```sh
curl -X POST 'MEILISEARCH_URL/indexes/profiles' -H 'Content-Type: application/json' --data-binary @crm-profiles.json &&
curl -X POST 'MEILISEARCH_URL/indexes/chats' -H 'Content-Type: application/json' --data-binary @crm-chats.json &&
curl -X POST 'MEILISEARCH_URL/indexes/tickets' -H 'Content-Type: application/json' --data-binary @crm-tickets.json
```

[Use the tasks endpoint](/learn/async/working_with_tasks) to check the indexing status. Once Meilisearch successfully indexed all three datasets, you are ready to perform a federated search.

## Perform a federated search

When you are looking for Natasha Nguyen's email address in your CRM application, you may not know whether you will find it in a chat log, among the existing customer profiles, or in a recent support ticket. In this situation, you can use federated search to search across all possible sources and receive a single list of results.

Use the `/multi-search` endpoint with the `federation` parameter to query the three indexes simultaneously:

```sh
curl \
 -X POST 'MEILISEARCH_URL/multi-search' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "federation": {},
 "queries": [
 {
 "indexUid": "chats",
 "q": "natasha"
 },
 {
 "indexUid": "profiles",
 "q": "natasha"
 },
 {
 "indexUid": "tickets",
 "q": "natasha"
 }
 ]
 }'
```

Meilisearch should respond with a single list of search results:

```json
{
 "hits": [
 {
 "id": 0,
 "client_name": "Natasha Nguyen",
 "message": "My email is natasha.nguyen@example.com",
 "time": 1727349362,
 "_federation": {
 "indexUid": "chats",
 "queriesPosition": 0
 }
 },
 …
 ],
 "processingTimeMs": 0,
 "limit": 20,
 "offset": 0,
 "estimatedTotalHits": 3,
 "semanticHitCount": 0
}
```

## Promote results from a specific index

Since this is a CRM application, users have profiles with their preferred contact information. If you want to search for Riccardo Rotondo's preferred email, you can boost documents in the `profiles` index.

Use the `weight` property of the `federation` parameter to boost results coming from a specific query:

```sh
curl \
 -X POST 'MEILISEARCH_URL/multi-search' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "federation": {},
 "queries": [
 {
 "indexUid": "chats",
 "q": "rotondo"
 },
 {
 "indexUid": "profiles",
 "q": "rotondo",
 "federationOptions": {
 "weight": 1.2
 }
 },
 {
 "indexUid": "tickets",
 "q": "rotondo"
 }
 ]
 }'
```

This request will lead to results from the query targeting `profile` ranking higher than documents from other queries:

```json
{
 "hits": [
 {
 "id": 1,
 "name": "Riccardo Rotondo",
 "email": "riccardo.rotondo@example.com",
 "_federation": {
 "indexUid": "profiles",
 "queriesPosition": 1
 }
 },
 …
 ],
 "processingTimeMs": 0,
 "limit": 20,
 "offset": 0,
 "estimatedTotalHits": 3,
 "semanticHitCount": 0
}
```

## Conclusion

You have created three indexes, then performed a federated multi-index search to receive all results in a single list. You then used `weight` to boost results from the index most likely to contain the information you wanted.

---

## Performing personalized search queries

## Requirements

- A Meilisearch project
- Self-hosted Meilisearch users: a Cohere API key

## Activate personalized search

### Cloud users

Open a support ticket requesting Meilisearch to activate search personalization for your project.

### Self-hosted users

Relaunch your instance using the search personalization instance option:

```sh
Meilisearch --experimental-personalization-api-key="COHERE_API_KEY"
```

## Generating user context

Search personalization requires a description about the user performing the search. Meilisearch does not currently provide automated generation of user context.

You’ll need to **dynamically generate a plain-text user description** for each search request. This should summarize relevant traits, such as:

- Category preferences, like brand or size
- Price sensitivity, like budget-conscious
- Possible use cases, such as fitness and sport
- Other assorted information, such as general interests or location

The re-ranking model is optimized to favor positive signals. For best results, focus on affirmatively stated preferences, behaviors, and affinities, such as "likes the color red" and "prefers cheaper brands" over "dislikes blue" and "is not interested in luxury brands".

## Perform a personalized search

Once search personalization is active and you have a pipeline in place to generate user profiles, you are ready to perform personalized searches.

Submit a search query and include the `personalize` search parameter. `personalize` must be an object with a single field, `userContext`. Use the description you generated in the previous step as the value for `userContext`:

```sh
curl \
 -X POST 'MEILISEARCH_URL/indexes/INDEX_NAME/search' \
 -H 'Content-Type: application/json' \
 --data-binary '{ 
 "q": "wireless keyboard",
 "personalize": {
 "userContext": "The user prefers compact mechanical keyboards from Keychron or Logitech, with a mid-range budget and quiet keys for remote work."
 }
 }'
```

---

## What is search personalization?

Search personalization uses AI technology to re-rank search results at query time based on the user context you provide.

## Why use search personalization?

Not everyone search the same way. Personalizing search results allows you to adapt relevance to each user’s preferences, behavior, or intent.

e.g., in an e-commerce site, someone who often shops for sportswear might see sneakers and activewear ranked higher when searching for “shoes”. A user interested in luxury fashion might see designer heels or leather boots first instead.

## How does search personalization work?

1. First generate a plain-text description of the user: `"The user prefers genres like Documentary, Music, Drama"`
2. When the user performs a search, you submit their description together their search request
3. Meilisearch retrieves documents based on the user's query as usual
4. Finally, the re-ranking model reorders results based on the user context you provided in the first step

## How to enable search personalization in Meilisearch?

Search personalization is an experimental feature.

If you are a Cloud user, contact support to activate it for your projects.

If you are self-hosting Meilisearch, relaunch it using the [search personalization instance option](/learn/self_hosted/configure_meilisearch_at_launch#search-personalization).

Consult the [search personalization guide](/learn/personalization/making_personalized_search_queries) for more information on how to implement it in your application.

---

## Attribute ranking order

In most datasets, some fields are more relevant to search than others. A `title`, e.g., might be more meaningful to a movie search than its `overview` or its `release_date`.

When `searchableAttributes` is using its default value, `[*]`, all fields carry the same weight.

If you manually configure [the searchable attributes list](/learn/relevancy/displayed_searchable_attributes#the-searchableattributes-list), attributes that appear early in the array are more important when calculating search result relevancy.

## Example

```json
[
 "title",
 "overview",
 "release_date"
]
```

With the above attribute ranking order, matching words found in the `title` field would have a higher impact on relevancy than the same words found in `overview` or `release_date`. If you searched for "1984", e.g., results like Michael Radford's film "1984" would be ranked higher than movies released in the year 1984.

## Attribute ranking order and nested objects

By default, nested fields share the same weight as their parent attribute. Use dot notation to set different weights for attributes in nested objects:

```json
[
 "title",
 "review.critic",
 "overview",
 "review.user"
]
```

With the above ranking order, `review.critic` becomes more important than its sibling `review.user` when calculating a document's ranking score.

The `attribute` rule's position in [`rankingRules`](/learn/relevancy/ranking_rules) determines how the results are sorted. Meaning, **if `attribute` is at the bottom of the ranking rules list, it will have almost no impact on your search results.**

---

## Custom ranking rules

There are two types of ranking rules in Meilisearch: [built-in ranking rules](/learn/relevancy/ranking_rules) and custom ranking rules. This article describes the main aspects of using and configuring custom ranking rules.

## Ascending and descending sorting rules

Meilisearch supports two types of custom rules: one for ascending sort and one for descending sort.

To add a custom ranking rule, you have to communicate the attribute name followed by a colon (`:`) and either `asc` for ascending order or `desc` for descending order.

- To apply an **ascending sort** (results sorted by increasing value of the attribute): `attribute_name:asc`

- To apply a **descending sort** (results sorted by decreasing value of the attribute): `attribute_name:desc`

**The attribute must have either a numeric or a string value** in all of the documents contained in that index.

You can add this rule to the existing list of ranking rules using the [update settings endpoint](/reference/api/settings#update-settings) or [update ranking rules endpoint](/reference/api/settings#update-ranking-rules).

## How to use custom ranking rules

Custom ranking rules sort results in lexicographical order. e.g., `Elena` will rank higher than `Ryu` and lower than `11` in a descending sort.

Since this operation does not take into consideration document relevancy, in the majority of cases you should place custom ranking rules after the built-in ranking rules. This ensures that results are first sorted by relevancy, and the lexicographical sorting takes place only when two or more documents share the same ranking score.

Setting a custom ranking rule at a high position may result in a degraded search experience, since users will see documents in alphanumerical order instead of sorted by relevance.

## Example

Suppose you have a movie dataset. The documents contain the fields `release_date` with a timestamp as value, and `movie_ranking`, an integer that represents its ranking.

The following example creates a rule that makes older movies more relevant than recent ones. A movie released in 1999 will appear before a movie released in 2020.

```
release_date:asc
```

The following example will create a rule that makes movies with a good rank more relevant than movies with a lower rank. Movies with a higher ranking will appear first.

```
movie_ranking:desc
```

The following array includes all built-in ranking rules and places the custom rules at the bottom of the processing order:

```json
[
 "words",
 "typo",
 "proximity",
 "attribute",
 "sort",
 "exactness",
 "release_date:asc",
 "movie_ranking:desc"
]
```

## Sorting at search time and custom ranking rules

Meilisearch allows users to define [sorting order at query time](/learn/filtering_and_sorting/sort_search_results) by using the [`sort` search parameter](/reference/api/search#sort). There is some overlap between sorting and custom ranking rules, but the two do have different uses.

In general, `sort` will be most useful when you want to allow users to define what type of results they want to see first. A good use-case for `sort` is creating a webshop interface where customers can sort products by descending or ascending product price.

Custom ranking rules, instead, are always active once configured and are useful when you want to promote certain types of results. A good use-case for custom ranking rules is ensuring discounted products in a webshop always feature among the top results.

Meilisearch does not offer native support for promoting, pinning, and boosting specific documents so they are displayed more prominently than other search results. Consult these Meilisearch blog articles for workarounds on [implementing promoted search results with React InstantSearch](https://blog.meilisearch.com/promoted-search-results-with-react-instantsearch) and [document boosting](https://blog.meilisearch.com/document-boosting).

---

## Displayed and searchable attributes

import CodeSamplesFieldPropertiesGuideDisplayed1 from '/snippets/samples/code_samples_field_properties_guide_displayed_1.mdx';
import CodeSamplesFieldPropertiesGuideSearchable1 from '/snippets/samples/code_samples_field_properties_guide_searchable_1.mdx';

By default, whenever a document is added to Meilisearch, all new attributes found in it are automatically added to two lists:

- [`displayedAttributes`](/learn/relevancy/displayed_searchable_attributes#displayed-fields): Attributes whose fields are displayed in documents
- [`searchableAttributes`](/learn/relevancy/displayed_searchable_attributes#the-searchableattributes-list): Attributes whose values are searched for matching query words

By default, every field in a document is **displayed** and **searchable**. These properties can be modified in the [settings](/reference/api/settings).

## Displayed fields

The fields whose attributes are added to the [`displayedAttributes` list](/reference/api/settings#displayed-attributes) are **displayed in each matching document**.

Documents returned upon search contain only displayed fields. If a field attribute is not in the displayed-attribute list, the field won't be added to the returned documents.

**By default, all field attributes are set as displayed**.

### Example

Suppose you manage a database that contains information about movies. By adding the following settings, documents returned upon search will contain the fields `title`, `overview`, `release_date` and `genres`.

## Searchable fields

A field can either be **searchable** or **non-searchable**.

When you perform a search, all searchable fields are checked for matching query words and used to assess document relevancy, while non-searchable fields are ignored entirely. **By default, all fields are searchable.**

Non-searchable fields are most useful for internal information that's not relevant to the search experience, such as URLs, sales numbers, or ratings used exclusively for sorting results.

Even if you make a field non-searchable, it will remain [stored in the database](#data-storing) and can be made searchable again at a later time.

### The `searchableAttributes` list

Meilisearch uses an ordered list to determine which attributes are searchable. The order in which attributes appear in this list also determines their [impact on relevancy](/learn/relevancy/attribute_ranking_order), from most impactful to least.

In other words, the `searchableAttributes` list serves two purposes:

1. It designates the fields that are searchable 
2. It dictates the [attribute ranking order](/learn/relevancy/attribute_ranking_order)

There are two possible modes for the `searchableAttributes` list.

#### Default: Automatic

**By default, all attributes are automatically added to the `searchableAttributes` list in their order of appearance.** This means that the initial order will be based on the order of attributes in the first document indexed, with each new attribute found in subsequent documents added at the end of this list.

This default behavior is indicated by a `searchableAttributes` value of `["*"]`. To verify the current value of your `searchableAttributes` list, use the [get searchable attributes endpoint](/reference/api/settings#get-searchable-attributes).

If you'd like to restore your searchable attributes list to this default behavior, [set `searchableAttributes` to an empty array `[]`](/reference/api/settings#update-searchable-attributes) or use the [reset searchable attributes endpoint](/reference/api/settings#reset-searchable-attributes).

#### Manual

You may want to make some attributes non-searchable, or change the [attribute ranking order](/learn/relevancy/attribute_ranking_order) after documents have been indexed. To do so, place the attributes in the desired order and send the updated list using the [update searchable attributes endpoint](/reference/api/settings#update-searchable-attributes).

After manually updating the `searchableAttributes` list, **subsequent new attributes will no longer be automatically added** unless the settings are [reset](/reference/api/settings#reset-searchable-attributes).

Due to an implementation bug, manually updating `searchableAttributes` will change the displayed order of document fields in the JSON response. This behavior is inconsistent and will be fixed in a future release.

#### Example

Suppose that you manage a database of movies with the following fields: `id`, `overview`, `genres`, `title`, `release_date`. These fields all contain useful information. However, **some are more useful to search than others**. To make the `id` and `release_date` fields non-searchable and re-order the remaining fields by importance, you might update the searchable attributes list in the following way.

### Customizing attributes to search on at search time

By default, all queries search through all attributes in the `searchableAttributes` list. Use [the `attributesToSearchOn` search parameter](/reference/api/search#customize-attributes-to-search-on-at-search-time) to restrict specific queries to a subset of your index's `searchableAttributes`.

## Data storing

All fields are stored in the database. **This behavior cannot be changed**.

Thus, even if a field is missing from both the `displayedAttributes` list and the `searchableAttributes` list, **it is still stored in the database** and can be added to either or both lists at any time.

---

## Distinct attribute

import CodeSamplesDistinctAttributeGuide1 from '/snippets/samples/code_samples_distinct_attribute_guide_1.mdx';
import CodeSamplesDistinctAttributeGuideFilterable1 from '/snippets/samples/code_samples_distinct_attribute_guide_filterable_1.mdx';
import CodeSamplesDistinctAttributeGuideDistinctParameter1 from '/snippets/samples/code_samples_distinct_attribute_guide_distinct_parameter_1.mdx';

The distinct attribute is a special, user-designated field. It is most commonly used to prevent Meilisearch from returning a set of several similar documents, instead forcing it to return only one.

You may set a distinct attribute in two ways: using the `distinctAttribute` index setting during configuration, or the `distinct` search parameter at search time.

## Setting a distinct attribute during configuration

`distinctAttribute` is an index setting that configures a default distinct attribute Meilisearch applies to all searches and facet retrievals in that index.

There can be only one `distinctAttribute` per index. Trying to set multiple fields as a `distinctAttribute` will return an error.

The value of a field configured as a distinct attribute will always be unique among returned documents. This means **there will never be more than one occurrence of the same value** in the distinct attribute field among the returned documents.

When multiple documents have the same value for the distinct attribute, Meilisearch returns only the highest-ranked result after applying [ranking rules](/learn/relevancy/ranking_rules). If two or more documents are equivalent in terms of ranking, Meilisearch returns the first result according to its `internal_id`.

## Example

Suppose you have an e-commerce dataset. For an index that contains information about jackets, you may have several identical items with minor variations such as color or size.

As shown below, this dataset contains three documents representing different versions of a Lee jeans leather jacket. One of the jackets is brown, one is black, and the last one is blue.

```json
[
 {
 "id": 1,
 "description": "Leather jacket",
 "brand": "Lee jeans",
 "color": "brown",
 "product_id": "123456"
 },
 {
 "id": 2,
 "description": "Leather jacket",
 "brand": "Lee jeans",
 "color": "black",
 "product_id": "123456"
 },
 {
 "id": 3,
 "description": "Leather jacket",
 "brand": "Lee jeans",
 "color": "blue",
 "product_id": "123456"
 }
]
```

By default, a search for `lee leather jacket` would return all three documents. This might not be desired, since displaying nearly identical variations of the same item can make results appear cluttered.

In this case, you may want to return only one document with the `product_id` corresponding to this Lee jeans leather jacket. To do so, you could set `product_id` as the `distinctAttribute`.

By setting `distinctAttribute` to `product_id`, search requests **will never return more than one document with the same `product_id`**.

After setting the distinct attribute as shown above, querying for `lee leather jacket` would only return the first document found. The response would look like this:

```json
{
 "hits": [
 {
 "id": 1,
 "description": "Leather jacket",
 "brand": "Lee jeans",
 "color": "brown",
 "product_id": "123456"
 }
 ],
 "offset": 0,
 "limit": 20,
 "estimatedTotalHits": 1,
 "processingTimeMs": 0,
 "query": "lee leather jacket"
}
```

For more in-depth information on distinct attribute, consult the [API reference](/reference/api/settings#distinct-attribute).

## Setting a distinct attribute at search time

`distinct` is a search parameter you may add to any search query. It allows you to selectively use distinct attributes depending on the context. `distinct` takes precedence over `distinctAttribute`.

To use an attribute with `distinct`, first add it to the `filterableAttributes` list:

Then use `distinct` in a search query, specifying one of the configured attributes:

---

## Built-in ranking rules

There are two types of ranking rules in Meilisearch: built-in ranking rules and [custom ranking rules](/learn/relevancy/custom_ranking_rules). This article describes the main aspects of using and configuring built-in ranking rules.

Built-in ranking rules are the core of Meilisearch's relevancy calculations.

## List of built-in ranking rules

Meilisearch contains six built-in ranking rules in the following order:

```json
[
 "words",
 "typo",
 "proximity",
 "attribute",
 "sort",
 "exactness"
]
```

Depending on your needs, you might want to change this order. To do so, use the [update settings endpoint](/reference/api/settings#update-settings) or [update ranking rules endpoint](/reference/api/settings#update-ranking-rules).

## 1. Words

Results are sorted by **decreasing number of matched query terms**. Returns documents that contain all query terms first.

To ensure optimal relevancy, **Meilisearch always sort results as if the `words` ranking rule were present** with a higher priority than the attributes, exactness, typo and proximity ranking rules. This happens even if `words` has been removed or set with a lower priority.

The `words` rule works from right to left. Therefore, the order of the query string impacts the order of results.

e.g., if someone were to search `batman dark knight`, the `words` rule would rank documents containing all three terms first, documents containing only `batman` and `dark` second, and documents containing only `batman` third.

## 2. Typo

Results are sorted by **increasing number of typos**. Returns documents that match query terms with fewer typos first.

## 3. Proximity

Results are sorted by **increasing distance between matched query terms**. Returns documents where query terms occur close together and in the same order as the query string first.

[It is possible to lower the precision of this ranking rule.](/reference/api/settings#proximity-precision) This may significantly improve indexing performance. In a minority of use cases, lowering precision may also lead to lower search relevancy for queries using multiple search terms.

## 4. Attribute

Results are sorted according to the **[attribute ranking order](/learn/relevancy/attribute_ranking_order)**. Returns documents that contain query terms in more important attributes first.

Also, note the documents with attributes containing the query words at the beginning of the attribute will be considered more relevant than documents containing the query words at the end of the attributes.

## 5. Sort

Results are sorted **according to parameters decided at query time**. When the `sort` ranking rule is in a higher position, sorting is exhaustive: results will be less relevant but follow the user-defined sorting order more closely. When `sort` is in a lower position, sorting is relevant: results will be very relevant but might not always follow the order defined by the user.

Differently from other ranking rules, sort is only active for queries containing the [`sort` search parameter](/reference/api/search#sort). If a search request does not contain `sort`, or if its value is invalid, this rule will be ignored.

## 6. Exactness

Results are sorted by **the similarity of the matched words with the query words**. Returns documents that contain exactly the same terms as the ones queried first.

## Examples

 <img src="/assets/images/ranking-rules/vogli3.png" alt="Demonstrating the typo ranking rule by searching for 'vogli'" />

### Typo

- `vogli`: 0 typo
- `volli`: 1 typo

The `typo` rule sorts the results by increasing number of typos on matched query words.

 <img src="/assets/images/ranking-rules/new_road.png" alt="Demonstrating the proximity ranking rule by searching for 'new road'" />

### Proximity

The reason why `Creature` is listed before `Mississippi Grind` is because of the `proximity` rule. The smallest **distance** between the matching words in `creature` is smaller than the smallest **distance** between the matching words in `Mississippi Grind`.

The `proximity` rule sorts the results by increasing distance between matched query terms.

 <img src="/assets/images/ranking-rules/belgium.png" alt="Demonstrating the attribute ranking rule by searching for 'belgium'" />

### Attribute

`If It's Tuesday, This must be Belgium` is the first document because the matched word `Belgium` is found in the `title` attribute and not the `overview`.

The `attribute` rule sorts the results by [attribute importance](/learn/relevancy/attribute_ranking_order).

 <img src="/assets/images/ranking-rules/knight.png" alt="Demonstrating the exactness ranking rule by searching for 'Knight'" />

### Exactness

`Knight Moves` is displayed before `Knights of Badassdom`. `Knight` is exactly the same as the search query `Knight` whereas there is a letter of difference between `Knights` and the search query `Knight`.

---

## Ranking score

When using the [`showRankingScore` search parameter](/reference/api/search#ranking-score), Meilisearch adds a global ranking score field, `_rankingScore`, to each document. The `_rankingScore` is between `0.0` and `1.0`. The higher the ranking score, the more relevant the document.

Ranking rules sort documents either by relevancy (`words`, `typo`, `proximity`, `exactness`, `attribute`) or by the value of a field (`sort`). Since `sort` doesn't rank documents by relevancy, it does not influence the `_rankingScore`.

A document's ranking score does not change based on the scores of other documents in the same index.

e.g., if a document A has a score of `0.5` for a query term, this value remains constant no matter the score of documents B, C, or D.

The table below details all the index settings that can influence the `_rankingScore`. **Unlisted settings do not influence the ranking score.** | Index setting | Influences if | Rationale | | :--- | :--- | :--- | | `searchableAttributes` | The `attribute` ranking rule is used | The `attribute` ranking rule rates the document depending on the attribute in which the query terms show up. The order is determined by `searchableAttributes` | | `rankingRules` | Always | The score is computed by computing the subscore of each ranking rule with a weight that depends on their order | | `stopWords` | Always | Stop words influence the `words` ranking rule, which is almost always used | | `synonyms` | Always | Synonyms influence the `words` ranking rule, which is almost always used | | `typoTolerance` | The `typo` ranking rule is used | Used to compute the maximum number of typos for a query | ---

## Relevancy

**Relevancy** refers to the accuracy and effectiveness of search results. If search results are almost always appropriate, then they can be considered relevant, and vice versa.

Meilisearch has a number of features for fine-tuning the relevancy of search results. The most important tool among them is **ranking rules**. There are two types of ranking rules: [built-in ranking rules](/learn/relevancy/ranking_rules) and custom ranking rules.

## Behavior

Each index possesses a list of ranking rules stored as an array in the [settings object](/reference/api/settings). This array is fully customizable, meaning you can delete existing rules, add new ones, and reorder them as needed.

Meilisearch uses a [bucket sort](https://en.wikipedia.org/wiki/Bucket_sort) algorithm to rank documents whenever a search query is made. The first ranking rule applies to all documents, while each subsequent rule is only applied to documents considered equal under the previous rule as a tiebreaker.

**The order in which ranking rules are applied matters.** The first rule in the array has the most impact, and the last rule has the least. Our default configuration meets most standard needs, but [you can change it](/reference/api/settings#update-ranking-rules).

Deleting a rule means that Meilisearch will no longer sort results based on that rule. e.g., **if you delete the [typo ranking rule](/learn/relevancy/ranking_rules#2-typo), documents with typos will still be considered during search**, but they will no longer be sorted by increasing number of typos.

---

## Synonyms

import CodeSamplesSynonymsGuide1 from '/snippets/samples/code_samples_synonyms_guide_1.mdx';

If multiple words have an equivalent meaning in your dataset, you can [create a list of synonyms](/reference/api/settings#update-synonyms). This will make your search results more relevant.

Words set as synonyms won't always return the same results. With the default settings, the `movies` dataset should return 547 results for `great` and 66 for `fantastic`. Let's set them as synonyms:

With the new settings, searching for `great` returns 595 results and `fantastic` returns 423 results. This is due to various factors like [typos](/learn/relevancy/typo_tolerance_settings#minwordsizefortypos) and [splitting the query](/learn/engine/concat#split-queries) to find relevant documents. The search for `great` will allow only one typo (e.g., `create`) and take into account all variations of `great` (for instance, `greatest`) along with `fantastic`.

The number of search results may vary depending on changes to the `movies` dataset.

## Normalization

All synonyms are **lowercased** and **de-unicoded** during the indexing process.

### Example

Consider a situation where `Résumé` and `CV` are set as synonyms.

```json
{
 "Résumé": [
 "CV"
 ],
 "CV": [
 "Résumé"
 ]
}
```

A search for `cv` would return any documents containing `cv` or `CV`, in addition to any that contain `Résumé`, `resumé`, `resume`, etc., unaffected by case or accent marks.

## One-way association

Use this when you want one word to be synonymous with another, but not the other way around.

```
phone => iphone
```

A search for `phone` will return documents containing `iphone` as if they contained the word `phone`.

However, if you search for `iphone`, documents containing `phone` will be ranked lower in the results due to [the typo rule](/learn/relevancy/ranking_rules).

### Example

To create a one-way synonym list, this is the JSON syntax that should be [added to the settings](/reference/api/settings#update-synonyms).

```json
{
 "phone": [
 "iphone"
 ]
}
```

## Relevancy

**The exact search query will always take precedence over its synonyms.** The `exactness` ranking rule favors exact words over synonyms when ranking search results.

Taking the following set of search results:

```json
[
 {
 "id": 0,
 "title": "Ghouls 'n Ghosts"
 },
 {
 "id": 1,
 "title": "Phoenix Wright: Spirit of Justice"
 }
]
```

If you configure `ghost` as a synonym of `spirit`, queries searching for `spirit` will return document `1` before document `0`.

## Mutual association

By associating one or more synonyms with each other, they will be considered the same in both directions.

```
shoe <=> boot <=> slipper <=> sneakers
```

When a search is done with one of these words, all synonyms will be considered as the same word and will appear in the search results.

### Example

To create a mutual association between four words, this is the JSON syntax that should be [added to the settings](/reference/api/settings#update-synonyms).

```json
{
 "shoe": [
 "boot",
 "slipper",
 "sneakers"
 ],
 "boot": [
 "shoe",
 "slipper",
 "sneakers"
 ],
 "slipper": [
 "shoe",
 "boot",
 "sneakers"
 ],
 "sneakers": [
 "shoe",
 "boot",
 "slipper"
 ]
}
```

## Multi-word synonyms

Meilisearch treats multi-word synonyms as [phrases](/reference/api/search#phrase-search).

### Example

Suppose you set `San Francisco` and `SF` as synonyms with a [mutual association](#mutual-association)

```json
{
 "san francisco": [
 "sf"
 ],
 "sf": [
 "san francisco"
 ]
}
```

If you input `SF` as a search query, Meilisearch will also return results containing the phrase `San Francisco`. However, depending on the ranking rules, they might be considered less [relevant](/learn/relevancy/relevancy) than those containing `SF`. The reverse is also true: if your query is `San Francisco`, documents containing `San Francisco` may rank higher than those containing `SF`.

## Maximum number of synonyms per term

A single term may have up to 50 synonyms. Meilisearch silently ignores any synonyms beyond this limit. e.g., if you configure 51 synonyms for `book`, Meilisearch will only return results containing the term itself and the first 50 synonyms.

If any synonyms for a term contain more than one word, the sum of all words across all synonyms for that term cannot exceed 100 words. Meilisearch silently ignores any synonyms beyond this limit. e.g., if you configure 40 synonyms for `computer` in your application, taken together these synonyms must contain fewer than 100 words.

---

## Typo tolerance calculations

Typo tolerance helps users find relevant results even when their search queries contain spelling mistakes or typos, e.g., typing `phnoe` instead of `phone`. You can [configure the typo tolerance feature for each index](/reference/api/settings#update-typo-tolerance-settings).

Meilisearch uses a prefix [Levenshtein algorithm](https://en.wikipedia.org/wiki/Levenshtein_distance) to determine if a word in a document could be a possible match for a query term.

The [number of typos referenced above](/learn/relevancy/typo_tolerance_settings#minwordsizefortypos) is roughly equivalent to Levenshtein distance. The Levenshtein distance between two words _M_ and _P_ can be thought of as "the minimum cost of transforming _M_ into _P_" by performing the following elementary operations on _M_:

- substitution of a character (e.g., `kitten` → `sitten`)
- insertion of a character (e.g., `siting` → `sitting`)
- deletion of a character (e.g., `saturday` → `satuday`)

By default, Meilisearch uses the following rules for matching documents. Note that these rules are **by word** and not for the whole query string.

- If the query word is between `1` and `4` characters, **no typo** is allowed. Only documents that contain words that **start with** or are of the **same length** with this query word are considered valid
- If the query word is between `5` and `8` characters, **one typo** is allowed. Documents that contain words that match with **one typo** are retained for the next steps.
- If the query word contains more than `8` characters, we accept a maximum of **two typos**

This means that `saturday` which is `7` characters long, uses the second rule and matches every document containing **one typo**. e.g.:

- `saturday` is accepted because it is the same word
- `satuday` is accepted because it contains **one typo**
- `sutuday` is not accepted because it contains **two typos**
- `caturday` is not accepted because it contains **two typos** (as explained [above](/learn/relevancy/typo_tolerance_settings#minwordsizefortypos), a typo on the first letter of a word is treated as two typos)

## Impact of typo tolerance on the `typo` ranking rule

The [`typo` ranking rule](/learn/relevancy/ranking_rules#2-typo) sorts search results by increasing number of typos on matched query words. Documents with 0 typos will rank highest, followed by those with 1 and then 2 typos.

The presence or absence of the `typo` ranking rule has no impact on the typo tolerance setting. However, **[disabling the typo tolerance setting](/learn/relevancy/typo_tolerance_settings#enabled) effectively also disables the `typo` ranking rule.** This is because all returned documents will contain `0` typos.

To summarize:

- Typo tolerance affects how lenient Meilisearch is when matching documents
- The `typo` ranking rule affects how Meilisearch sorts its results
- Disabling typo tolerance also disables `typo`

---

## Typo tolerance settings

import CodeSamplesTypoToleranceGuide1 from '/snippets/samples/code_samples_typo_tolerance_guide_1.mdx';
import CodeSamplesTypoToleranceGuide4 from '/snippets/samples/code_samples_typo_tolerance_guide_4.mdx';
import CodeSamplesTypoToleranceGuide3 from '/snippets/samples/code_samples_typo_tolerance_guide_3.mdx';
import CodeSamplesTypoToleranceGuide2 from '/snippets/samples/code_samples_typo_tolerance_guide_2.mdx';

Typo tolerance helps users find relevant results even when their search queries contain spelling mistakes or typos, e.g., typing `phnoe` instead of `phone`. You can [configure the typo tolerance feature for each index](/reference/api/settings#update-typo-tolerance-settings).

## `enabled`

Typo tolerance is enabled by default, but you can disable it if needed:

With typo tolerance disabled, Meilisearch no longer considers words that are a few characters off from your query terms as matches. e.g., a query for `phnoe` will no longer return a document containing the word `phone`.

**In most cases, keeping typo tolerance enabled results in a better search experience.** Massive or multilingual datasets may be exceptions, as typo tolerance can cause false-positive matches in these cases.

## `minWordSizeForTypos`

By default, Meilisearch accepts one typo for query terms containing five or more characters, and up to two typos if the term is at least nine characters long.

If your dataset contains `seven`, searching for `sevem` or `sevan` will match `seven`. But `tow` won't match `two` as it's less than `5` characters.

You can override these default settings using the `minWordSizeForTypos` object. The code sample below sets the minimum word size for one typo to `4` and the minimum word size for two typos to `10`.

When updating the `minWordSizeForTypos` object, keep in mind that:

- `oneTypo` must be greater than or equal to 0 and less than or equal to `twoTypos`
- `twoTypos` must be greater than or equal to `oneTypo` and less than or equal to `255`

To put it another way: `0 ≤ oneTypo ≤ twoTypos ≤ 255`.

We recommend keeping the value of `oneTypo` between `2` and `8` and the value of `twoTypos` between `4` and `14`. If either value is too low, you may get a large number of false-positive results. On the other hand, if both values are set too high, many search queries may not benefit from typo tolerance.

**Typo on the first character** 
Meilisearch considers a typo on a query's first character as two typos.

**Concatenation** 
When considering possible candidates for typo tolerance, Meilisearch will concatenate multiple search terms separated by a [space separator](/learn/engine/datatypes#string). This is treated as one typo. e.g., a search for `any way` would match documents containing `anyway`.

For more about typo calculations, [see below](/learn/relevancy/typo_tolerance_calculations).

## `disableOnWords`

You can disable typo tolerance for a list of query terms by adding them to `disableOnWords`. `disableOnWords` is case insensitive.

Meilisearch won't apply typo tolerance on the query term `Shrek` or `shrek` at search time to match documents.

## `disableOnAttributes`

You can disable typo tolerance for a specific [document attribute](/learn/getting_started/documents) by adding it to `disableOnAttributes`. The code sample below disables typo tolerance for `title`:

With the above settings, matches in the `title` attribute will not tolerate any typos. e.g., a search for `beautiful` (9 characters) will not match the movie "Biutiful" starring Javier Bardem. With the default settings, this would be a match.

## `disableOnNumbers`

You can disable typo tolerance for all numeric values across all indexes and search requests by setting `disableOnNumbers` to `true`:

By default, typo tolerance on numerical values is turned on. This may lead to false positives, such as a search for `2024` matching documents containing `2025` or `2004`.

When `disableOnNumbers` is set to `true`, queries with numbers only return exact matches. Besides reducing the number of false positives, disabling typo tolerance on numbers may also improve indexing performance.

---

## Comparison to alternatives

There are many search engines on the web, both open-source and otherwise. Deciding which search solution is the best fit for your project is very important, but also difficult. In this article, we'll go over the differences between Meilisearch and other search engines:

- In the [comparison table](#comparison-table), we present a general overview of the differences between Meilisearch and other search engines

- In the [approach comparison](#approach-comparison), instead, we focus on how Meilisearch measures up against [ElasticSearch](#meilisearch-vs-elasticsearch) and [Algolia](#meilisearch-vs-algolia), currently two of the biggest solutions available in the market

- Finally, we end this article with [an in-depth analysis of the broader search engine landscape](#a-quick-look-at-the-search-engine-landscape)

Please be advised that many of the search products described below are constantly evolving—just like Meilisearch. These are only our own impressions, and may not reflect recent changes. If something appears inaccurate, please don't hesitate to open an [issue or pull request](https://github.com/meilisearch/documentation).

## Comparison table

### General overview | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | Source code licensing | [MIT](https://choosealicense.com/licenses/mit/) <br /> (Fully open-source) | Closed-source | [GPL-3](https://choosealicense.com/licenses/gpl-3.0/) <br /> (Fully open-source) | [AGPLv3](https://choosealicense.com/licenses/agpl-3.0/) <br /> (open-source) | | Built with | Rust <br /> [Check out why we believe in Rust](https://www.abetterinternet.org/docs/memory-safety/). | C++ | C++ | Java | | Data storage | Disk with Memory Mapping -- Not limited by RAM | Limited by RAM | Limited by RAM | Disk with RAM cache | ### Features

#### Integrations and SDKs

Note: we are only listing libraries officially supported by the internal teams of each different search engine. | SDK | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | REST API | ✅ | ✅ | ✅ | ✅ | | [JavaScript client](https://github.com/meilisearch/meilisearch-js) | ✅ | ✅ | ✅ | ✅ | | [PHP client](https://github.com/meilisearch/meilisearch-php) | ✅ | ✅ | ✅ | ✅ | | [Python client](https://github.com/meilisearch/meilisearch-python) | ✅ | ✅ | ✅ | ✅ | | [Ruby client](https://github.com/meilisearch/meilisearch-ruby) | ✅ | ✅ | ✅ | ✅ | | [Java client](https://github.com/meilisearch/meilisearch-java) | ✅ | ✅ | ✅ | ✅ | | [Swift client](https://github.com/meilisearch/meilisearch-swift) | ✅ | ✅ | ✅ | ❌ | | [.NET client](https://github.com/meilisearch/meilisearch-dotnet) | ✅ | ✅ | ✅ | ✅ | | [Rust client](https://github.com/meilisearch/meilisearch-rust) | ✅ | ❌ | 🔶 <br /> WIP | ✅ | | [Go client](https://github.com/meilisearch/meilisearch-go) | ✅ | ✅ | ✅ | ✅ | | [Dart client](https://github.com/meilisearch/meilisearch-dart) | ✅ | ✅ | ✅ | ❌ | | [Symfony](https://github.com/meilisearch/meilisearch-symfony) | ✅ | ✅ | ✅ | ❌ | | Django | ❌ | ✅ | ❌ | ❌ | | [Rails](https://github.com/meilisearch/meilisearch-rails) | ✅ | ✅ | 🔶 <br />WIP | ✅ || | [Official Laravel Scout Support](https://github.com/laravel/scout) | ✅ | ✅ | ✅ | ❌ <br /> Available as a standalone module | | [Instantsearch](https://github.com/meilisearch/meilisearch-js-plugins/tree/main/packages/instant-meilisearch) | ✅ | ✅ | ✅ | ✅ | | [Autocomplete](https://github.com/meilisearch/meilisearch-js-plugins/tree/main/packages/autocomplete-client) | ✅ | ✅ | ✅ | ✅ | | [Docsearch](https://github.com/meilisearch/docs-scraper) | ✅ | ✅ | ✅ | ❌ | | [Strapi](https://github.com/meilisearch/strapi-plugin-meilisearch) | ✅ | ✅ | ❌ | ❌ | | [Gatsby](https://github.com/meilisearch/gatsby-plugin-meilisearch) | ✅ | ✅ | ✅ | ❌ | | [Firebase](https://github.com/meilisearch/firestore-meilisearch) | ✅ | ✅ | ✅ | ❌ | #### Configuration

##### Document schema | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | Schemaless | ✅ | ✅ | 🔶 <br /> `id` field is required and must be a string | ✅ | | Nested field support | ✅ | ✅ | ✅ | ✅ | | Nested document querying | ❌ | ❌ | ❌ | ✅ | | Automatic document ID detection | ✅ | ❌ | ❌ | ❌ | | Native document formats | `JSON`, `NDJSON`, `CSV` | `JSON` | `NDJSON` | `JSON`, `NDJSON`, `CSV` | | Compression Support | Gzip, Deflate, and Brotli | Gzip | ❌ <br /> Reads payload as JSON which can lead to document corruption | Gzip | ##### Relevancy | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | Typo tolerant | ✅ | ✅ | ✅ | 🔶 <br />Needs to be specified by fuzzy queries | | Orderable ranking rules | ✅ | ✅ | 🔶 <br />Field weight can be changed, but ranking rules order cannot be changed. | ❌| | Custom ranking rules | ✅ | ✅ | ✅ | 🔶 <br />Function score query | | Query field weights | ✅ | ✅ | ✅ | ✅ | | Synonyms | ✅ | ✅ | ✅ | ✅ | | Stop words | ✅ | ✅ | ❌ | ✅ | | Automatic language detection | ✅ | ✅ | ❌ | ❌ | | All language supports | ✅ | ✅ | ✅ | ✅ | | Ranking Score Details | ✅ | ✅ | ❌ | ✅ | ##### Security | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | API Key Management | ✅ | ✅ | ✅ | ✅ | | Tenant tokens & multi-tenant indexes | ✅ <br /> [Multitenancy support](/learn/security/multitenancy_tenant_tokens) | ✅ | ✅ | ✅ <br /> Role-based | ##### Search | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | Placeholder search | ✅ | ✅ | ✅ | ✅ | | Multi-index search | ✅ | ✅ | ✅ | ✅ | | Federated search | ✅ | ❌ | ❌ | ✅ | | Exact phrase search | ✅ | ✅ | ✅ | ✅ | | Geo search | ✅ | ✅ | ✅ | ✅ | | Sort by | ✅ | 🔶 <br /> Limited to one `sort_by` rule per index. Indexes may have to be duplicated for each sort field and sort order | ✅ <br /> Up to 3 sort fields per search query | ✅ | | Filtering | ✅ <br /> Support complex filter queries with an SQL-like syntax. | 🔶 <br /> Does not support `OR` operation across multiple fields | ✅ | ✅ | | Faceted search | ✅ | ✅ | ✅ <br /> Faceted fields must be searchable <br /> Faceting can take several seconds when >10 million facet values must be returned | ✅ | | Distinct attributes <br /><div}>De-duplicate documents by a field value</div>| ✅ | ✅ | ✅ | ✅ | | Grouping <br /><div}>Bucket documents by field values</div> | ❌ | ✅ | ✅ | ✅ | ##### AI-powered search | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | Semantic Search | ✅ | 🔶 <br /> Under Premium plan | ✅ | ✅ | | Hybrid Search | ✅ | 🔶 <br /> Under Premium plan | ✅ | ✅ | | Embedding Generation | ✅ <br /> OpenAI <br /> HuggingFace <br /> REST embedders <br /> | Undisclosed | <br/> OpenAI <br /> GCP Vertex AI | ✅ <br /> ELSER <br/> E5 <br/> Cohere <br/> OpenAI <br/> Azure <br/> Google AI Studio <br/> Hugging Face <br/> | | Prompt Templates | ✅ | Undisclosed | ❌ | ❌ | | Vector Store | ✅ | Undisclosed | ✅ | ✅ | | Langchain Integration | ✅ | ❌ | ✅ | ✅ | | GPU support | ✅ <br /> CUDA | Undisclosed | ✅ <br /> CUDA | ❌ | ##### Visualize | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | [Mini Dashboard](https://github.com/meilisearch/mini-dashboard) | ✅ | 🔶 <br /> Cloud product | 🔶 <br /> Cloud product | ✅ | | Search Analytics | ✅ <br /> [Cloud product](https://www.meilisearch.com/cloud) | ✅ <br /> Cloud Product | ❌ | ✅ <br /> Cloud Product | | Monitoring Dashboard | ✅ <br /> [Cloud product](https://www.meilisearch.com/docs/learn/analytics/monitoring) | ✅ <br /> Cloud Product | ✅ <br /> Cloud Product | ✅ <br /> Cloud Product | #### Deployment | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | Self-hosted | ✅ | ❌ | ✅ | ✅ | | Platform Support | ARM <br /> x86 <br /> x64 | n/a | 🔶 ARM (requires Docker on macOS) <br /> x86 <br /> x64 | ARM <br /> x86 <br /> x64 | | Official 1-click deploy | ✅ <br /> [DigitalOcean](https://marketplace.digitalocean.com/apps/meilisearch) <br /> [Platform.sh](https://console.platform.sh/projects/create-project?template=https://raw.githubusercontent.com/platformsh/template-builder/master/templates/meilisearch/.platform.template.yaml) <br /> [Azure](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fcmaneu%2Fmeilisearch-on-azure%2Fmain%2Fmain.json) <br /> [Railway](https://railway.app/new/template/TXxa09?referralCode=YltNo3) <br /> [Koyeb](https://app.koyeb.com/deploy?type=docker&image=getmeili/meilisearch&name=meilisearch-on-koyeb&ports=7700;http;/&env%5BMEILI_MASTER_KEY%5D=REPLACE_ME_WITH_A_STRONG_KEY) | ❌ | 🔶 <br />Only for the cloud-hosted solution | ❌ | | Official cloud-hosted solution | [Cloud](https://www.meilisearch.com/cloud?utm_campaign=oss&utm_source=docs&utm_medium=comparison-table) | ✅ | ✅ | ✅ | | High availability | Available with [Cloud](https://www.meilisearch.com/cloud?utm_campaign=oss&utm_source=docs&utm_medium=comparison-table) | ✅ | ✅ | ✅ | | Run-time dependencies | None | N/A | None | None | | Backward compatibility | ✅ | N/A | ✅ | ✅ | | Upgrade path | Documents are automatically reindexed on upgrade | N/A | Documents are automatically reindexed on upgrade | Documents are automatically reindexed on upgrade, up to 1 major version | ### Limits | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | Maximum number of indexes | No limitation | 1000, increasing limit possible by contacting support | No limitation | No limitation | | Maximum index size | 80TiB | 128GB | Constrained by RAM | No limitation | | Maximum document size | No limitation | 100KB, configurable | No limitation | 100KB default, configurable | ### Community | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | GitHub stars of the main project | 42K | N/A | 17K | 66K | | Number of contributors on the main project | 179 | N/A | 38 | 1,900 | | Public Discord/Slack community size | 2,100 | N/A | 2,000 | 16K | ### Support | | Meilisearch | Algolia | Typesense | Elasticsearch | |---|:---:|:---:|:---:|:---:| | Status page | ✅ | ✅ | ✅ | ✅ | | Free support channels | Instant messaging / chatbox (2-3h delay),<br /> emails, <br /> public Discord community, <br /> GitHub issues & discussions | Instant messaging / chatbox, <br /> public community forum | Instant messaging/chatbox (24h-48h delay),<br /> public Slack community, <br /> GitHub issues. | Public Slack community, <br /> public community forum,<br /> GitHub issues | | Paid support channels | Slack Channel, emails, personalized support — whatever you need, we’ll be there! | Emails | Emails, <br /> phone, <br /> private Slack | Web support, <br /> emails, <br /> phone | ## Approach comparison

### Meilisearch vs Elasticsearch

Elasticsearch is designed as a backend search engine. Although it is not suited for this purpose, it is commonly used to build search bars for end-users.

Elasticsearch can handle searching through massive amounts of data and performing text analysis. to make it effective for end-user searching, you need to spend time understanding more about how Elasticsearch works internally to be able to customize and tailor it to fit your needs.

Unlike Elasticsearch, which is a general search engine designed for large amounts of log data (e.g., back-facing search), Meilisearch is intended to deliver performant instant-search experiences aimed at end-users (e.g., front-facing search).

Elasticsearch can sometimes be too slow if you want to provide a full instant search experience. Most of the time, it is significantly slower in returning search results compared to Meilisearch.

Meilisearch is a perfect choice if you need a simple and easy tool to deploy a typo-tolerant search bar. It provides prefix searching capability, makes search intuitive for users, and returns results instantly with excellent relevance out of the box.

For a more detailed analysis of how it compares with Meilisearch, refer to our [blog post on Elasticsearch](https://blog.meilisearch.com/meilisearch-vs-elasticsearch/?utm_campaign=oss&utm_source=docs&utm_medium=comparison).

### Meilisearch vs Algolia

Meilisearch was inspired by Algolia's product and the algorithms behind it. We indeed studied most of the algorithms and data structures described in their blog posts to implement our own. Meilisearch is thus a new search engine based on the work of Algolia and recent research papers.

Meilisearch provides similar features and reaches the same level of relevance just as quickly as its competitor.

If you are a current Algolia user considering a switch to Meilisearch, you may be interested in our [migration guide](/learn/update_and_migration/algolia_migration).

#### Key similarities

Some of the most significant similarities between Algolia and Meilisearch are:

- [Features](/learn/getting_started/what_is_meilisearch#features) such as search-as-you-type, typo tolerance, faceting, etc.
- Fast results targeting an instant search experience (answers < 50 milliseconds)
- Schemaless indexing
- Support for all JSON data types
- Asynchronous API
- Similar query response

#### Key differences

Contrary to Algolia, Meilisearch is open-source and can be forked or self-hosted.

Additionally, Meilisearch is written in Rust, a modern systems-level programming language. Rust provides speed, portability, and flexibility, which makes the deployment of our search engine inside virtual machines, containers, or even [Lambda@Edge](https://aws.amazon.com/lambda/edge/) a seamless operation.

#### Pricing

The [pricing model for Algolia](https://www.algolia.com/pricing/) is based on the number of records kept and the number of API operations performed. It can be prohibitively expensive for small and medium-sized businesses.

Meilisearch is an **open-source** search engine available via [Cloud](https://meilisearch.com/cloud?utm_campaign=oss&utm_source=docs&utm_medium=comparison) or self-hosted. Unlike Algolia, [Meilisearch pricing](https://www.meilisearch.com/pricing?utm_campaign=oss&utm_source=docs&utm_medium=comparison) is based on the number of documents stored and the number of search operations performed. However, Meilisearch offers a more generous free tier that allows more documents to be stored as well as fairer pricing for search usage. Meilisearch also offers a Pro tier for larger use cases to allow for more predictable pricing.

## A quick look at the search engine landscape

### Open source

#### Lucene

Apache Lucene is a free and open-source search library used for indexing and searching full-text documents. It was created in 1999 by Doug Cutting, who had previously written search engines at Xerox's Palo Alto Research Center (PARC) and Apple. Written in Java, Lucene was developed to build web search applications such as Google and DuckDuckGo, the last of which still uses Lucene for certain types of searches.

Lucene has since been divided into several projects:

- **Lucene itself**: the full-text search library.
- **Solr**: an enterprise search server with a powerful REST API.
- **Nutch**: an extensible and scalable web crawler relying on Apache Hadoop.

Since Lucene is the technology behind many open source or closed source search engines, it is considered as the reference search library.

#### Sonic

Sonic is a lightweight and schema-less search index server written in Rust. Sonic cannot be considered as an out-of-the-box solution, and compared to Meilisearch, it does not ensure relevancy ranking. Instead of storing documents, it comprises an inverted index with a Levenshtein automaton. This means any application querying Sonic has to retrieve the search results from an external database using the returned IDs and then apply some relevancy ranking.

Its ability to run on a few MBs of RAM makes it a minimalist and resource-efficient alternative to database tools that can be too heavyweight to scale.

#### Typesense

Like Meilisearch, Typesense is a lightweight open-source search engine optimized for speed. To better understand how it compares with Meilisearch, refer to our [blog post on Typesense](https://blog.meilisearch.com/meilisearch-vs-typesense/?utm_campaign=oss&utm_source=docs&utm_medium=comparison).

#### Lucene derivatives

#### Lucene-Solr

Solr is a subproject of Apache Lucene, created in 2004 by Yonik Seeley, and is today one of the most widely used search engines available worldwide. Solr is a search platform, written in Java, and built on top of Lucene. In other words, Solr is an HTTP wrapper around Lucene's Java API, meaning you can leverage all the features of Lucene by using it. In addition, Solr server is combined with Solr Cloud, providing distributed indexing and searching capabilities, thus ensuring high availability and scalability. Data is shared but also automatically replicated.
Furthermore, Solr is not only a search engine; it is often used as a document-structured NoSQL database. Documents are stored in collections, which can be comparable to tables in a relational database.

Due to its extensible plugin architecture and customizable features, Solr is a search engine with an endless number of use cases even though, since it can index and search documents and email attachments, it is specifically popular for enterprise search.

#### Bleve & Tantivy

Bleve and Tantivy are search engine projects, respectively written in Golang and Rust, inspired by Apache Lucene and its algorithms (e.g., tf-idf, short for term frequency-inverse document frequency). Such as Lucene, both are libraries to be used for any search project; however they are not ready-to-use APIs.

### Source available

#### Elasticsearch

Elasticsearch is a search engine based on the Lucene library and is most popular for full-text search. It provides a REST API accessed by JSON over HTTP. One of its key options, called index sharding, gives you the ability to divide indexes into physical spaces to increase performance and ensure high availability. Both Lucene and Elasticsearch have been designed for processing high-volume data streams, analyzing logs, and running complex queries. You can perform operations and analysis (e.g., calculate the average age of all users named "Thomas") on documents that match a specified query.

Today, Lucene and Elasticsearch are dominant players in the search engine landscape. They both are solid solutions for a lot of different use cases in search, and also for building your own recommendation engine. They are good general products, but they require to be configured properly to get similar results to those of Meilisearch or Algolia.

### Closed source

#### Algolia

Algolia is a company providing a search engine on a SaaS model. Its software is closed source. In its early stages, Algolia offered mobile search engines that could be embedded in apps, facing the challenge of implementing the search algorithms from scratch. From the very beginning, the decision was made to build a search engine directly dedicated to the end-users, specifically, implementing search within mobile apps or websites.
Algolia successfully demonstrated over the past few years how critical tolerating typos was to improve the users' experience, and in the same way, its impact on reducing bounce rate and increasing conversion.

Apart from Algolia, a wide choice of SaaS products are available on the Search Engine Market. Most of them use Elasticsearch and fine-tune its settings to have a custom and personalized solution.

#### Swiftype

Swiftype is a search service provider specialized in website search and analytics. Swiftype was founded in 2012 by Matt Riley and Quin Hoxie, and is now owned by Elastic since November 2017. It is an end-to-end solution built on top of Elasticsearch, meaning it has the ability to leverage the Elastic Stack.

#### Doofinder

Doofinder is a paid on-site search service i.e. developed to integrate into any website with very little configuration. Doofinder is used by online stores to increase their sales, aiming to facilitate the purchase process.

## Conclusions

Each Search solution fits best with the constraints of a particular use case. Since each type of search engine offers a unique set of features, it wouldn't be easy nor relevant to compare their performance. For instance, it wouldn't be fair to make a comparison of speed between Elasticsearch and Algolia over a product-based database. The same goes for a very large full text-based database.

We cannot, therefore, compare ourselves with Lucene-based or other search engines targeted to specific tasks.

In the particular use case we cover, the most similar solution to Meilisearch is Algolia.

While Algolia offers the most advanced and powerful search features, this efficiency comes with an expensive pricing. Moreover, their service is marketed to big companies.

Meilisearch is dedicated to all types of developers. Our goal is to deliver a developer-friendly tool, easy to install, and to deploy. Because providing an out-of-the-box awesome search experience for the end-users matters to us, we want to give everyone access to the best search experiences out there with minimum effort and without requiring any financial resources.

Usually, when a developer is looking for a search tool to integrate into their application, they will go for ElasticSearch or less effective choices. Even if Elasticsearch is not best suited for this use case, it remains a great source available solution. However, it requires technical know-how to execute advanced features and hence more time to customize it to your business.

We aim to become the default solution for developers.

---

## Contributing to our documentation

This documentation website is hosted in a [public GitHub repository](https://github.com/meilisearch/documentation). It is built with [Next.js](https://nextjs.org), written in [MDX](https://mdxjs.com), and deployed on [Vercel](https://www.vercel.com).

## Our documentation philosophy

Our documentation aims to be:

- **Efficient**: we don't want to waste anyone's time
- **Accessible**: reading the texts here shouldn't require native English or a computer science degree
- **Thorough**: the documentation website should contain all information anyone needs to use Meilisearch - **Open source**: this is a resource by Meilisearch users, for Meilisearch users

## Documentation repository and local development

The Meilisearch documentation repository only stores the content of the docs website. Because the code that makes up the website lives in another repository, **it is not possible to run a local copy of the documentation**.

### Handling images and other static assets

When contributing content to the Meilisearch docs, store screenshots, images, GIFs, and videos in the relevant directory under `/assets`.

The build process does not currently support static assets with relative paths. When adding them to a document, make sure the asset URL points to the raw GitHub file address:

```markdown
\!\[Image description\]\(https://raw.githubusercontent.com/meilisearch/documentation/[branch_name]/assets/images/[guide_name]/diagram.png\)
```

## How to contribute?

### Issues

The maintainers of Meilisearch's documentation use [GitHub Issues](https://github.com/meilisearch/documentation/issues/new) to track tasks. Helpful issues include:

- Notify the docs team about content i.e. inaccurate, outdated, or confusing
- Requests for new features such as versioning or an embedded console
- Requests for new content such as new guides and tutorials

Before opening an issue or PR, please look through our [open issues](https://github.com/meilisearch/documentation/issues) to see if one already exists for your problem. If yes, please leave a comment letting us know that you're waiting for a fix or willing to work on it yourself. If not, please open a new issue describing the problem and informing us whether you want to work on it or not.

We love issues at Meilisearch, because they help us do our jobs better. Nine times out of ten, the most useful contribution is a simple GitHub issue that points out a problem and proposes a solution.

#### Creating your first issue

To open an issue you need a [GitHub account](https://github.com). Create one if necessary, then follow these steps:

1. Log into your account
2. Go to the [Meilisearch Documentation repository](https://github.com/meilisearch/documentation)
3. Click on "Issues"
4. Use the search bar to check if somebody else has reported the same problem. If they have, upvote with a 👍 and **don't create a new issue**!
5. If no one reported the problem you experienced, click on "New issue"
6. Write a short and descriptive title, then add a longer summary explaining the issue. If you're reporting a bug, make sure to include steps to reproduce the error, as well as your OS and browser version
7. Click on "Submit new issue"
8. A member of our team should [get back to you](#how-we-review-contributions) shortly
9. Enjoy the feeling of a job well done! 🎉

### Pull requests

You can also improve the documentation by making a [pull request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests).

Pull requests ("PRs" for short) are requests to integrate changes into a GitHub repository. The simplest way to create a PR on our documentation is using the "Edit this page" link at the bottom left of every page.

Pull requests are particularly good when you want to:

- **Solve an [existing issue](https://github.com/meilisearch/documentation/issues)**
- Fix a small error, such as a typo or broken link
- Create or improve content about something you know very well—e.g., a guide on how to integrate Meilisearch with a tool you have mastered

In most cases, it is a good idea to [create an issue](#creating-your-first-issue) before making a PR. This allows you to coordinate with the documentation maintainers and find the best way of addressing the problem you want to solve.

#### Creating your first PR

To create a PR you need a [GitHub account](https://github.com). Create one if necessary, then follow these steps:

1. Go to the documentation page you'd like to edit, scroll down, and click "Edit this page" at the bottom left of the screen. This will take you to GitHub
2. If you're not already signed in, do so now. You may be prompted to create a [fork](https://docs.github.com/en/github/getting-started-with-github/fork-a-repo)
3. Use GitHub's text editor to update the page
4. Scroll down until you reach a box named "Propose changes"
5. Fill in the first field to give your PR a short and descriptive title—e.g., "Fix typo in search API reference"
6. Use the second field to add a more detailed explanation of the changes you're proposing
7. Click the "Propose changes" button to continue. You should see a page that says "Comparing changes"
8. Make sure the base repository is set to `meilisearch/documentation` and the base branch is set to `main`. You can ignore the remaining fields
9. This screen will also show you a "diff", which allows you to see the changes you made compared to what's currently published on the documentation website
10. Click "Create pull request"
11. **Congrats, you made your first PR!** A documentation maintainer will review your pull request shortly. They may ask for changes, so keep an eye on your GitHub notifications
12. If everything looks good, your work will be merged into the `main` branch and become part of the official documentation site. You are now a Meilisearch Contributor! 🚀

## How we review contributions

### How we review issues

When **reviewing issues**, we consider a few criteria:

1. Is this task a priority for the documentation maintainers?
2. Is the documentation website the best place for this information? Sometimes an idea might work better on our blog than the docs, or it might be more effective to link to an external resource than write and maintain it ourselves
3. If it's a bug report, can we reproduce the error?

If users show interest in an issue by upvoting or reporting similar problems, it is more likely the documentation will dedicate resources to that task.

### How we review PRs

For **reviewing contributor PRs**, we start by making sure the PR is up to our **quality standard**.

We ask the following questions:

1. Is the information **accurate**?
2. Is it **easy to understand**?
3. Do the code samples run without errors? Do they help users understand what we are explaining?
4. Is the English **clear and concise**? Can a non-native speaker understand it?
5. Is the grammar perfect? Are there any typos?
6. Can we shorten text **without losing any important information**?
7. Do the suggested changes require updating other pages in the documentation website?
8. In the case of new content, is the article in the right place? Should other articles in the documentation link to it?

Nothing makes us happier than a thoughtful and helpful PR. Your PRs often save us time and effort, and they make the documentation **even stronger**.

Our only major requirement for PR contributions is that the author responds to communication requests within a reasonable time frame.

Once you've opened a PR in this repository, one of our team members will stop by shortly to review it. If your PR is approved, nothing further is required from you. However, **if in seven days you have not responded to a request for further changes or more information, we will consider the PR abandoned and close it**.

If this happens to you and you think there has been some mistake, please let us know and we will try to rectify the situation.

## Contributing to Meilisearch There are many ways to contribute to Meilisearch directly as well, such as:

- Contributing to the [main engine](https://github.com/meilisearch/meilisearch/blob/main/CONTRIBUTING.md)
- Contributing to [our integrations](https://github.com/meilisearch/integration-guides)
 - [Creating an integration](https://github.com/meilisearch/integration-guides/blob/main/resources/build-integration.md)
- Creating written or video content (tutorials, blog posts, etc.)

There are also many valuable ways of supporting the above repositories:

- Giving feedback
- Suggesting features
- Creating tests
- Fixing bugs
- Adding content
- Developing features

---

## Experimental features overview

import CodeSamplesUpdateExperimentalFeatures1 from '/snippets/samples/code_samples_update_experimental_features_1.mdx';

Meilisearch periodically introduces new experimental features. Experimental features are not always ready for production, but offer functionality that might benefit some users.

An experimental feature's API can change significantly and become incompatible between releases. Keep this in mind when using experimental features in a production environment.

Meilisearch makes experimental features available expecting they will become stable in a future release, but this is not guaranteed.

## Activating experimental features

Experimental features fall into two groups based on how they are activated or deactivated:

1. Those that are activated at launch with a command-line flag or environment variable
2. Those that are activated with the [`/experimental-features` API route](/reference/api/experimental_features).

## Activating experimental features at launch

Some experimental features can be [activated at launch](/learn/self_hosted/configure_meilisearch_at_launch), e.g. with a command-line flag:

```sh
./Meilisearch --experimental-enable-metrics
```

Flags and environment variables for experimental features are not included in the [regular configuration options list](/learn/self_hosted/configure_meilisearch_at_launch#all-instance-options). Instead, consult the specific documentation page for the feature you are interested in, which can be found in the experimental section.

Command-line flags for experimental features are always prefixed with `--experimental`. Environment variables for experimental features are always prefixed with `MEILI_EXPERIMENTAL`.

Activating or deactivating experimental features this way requires you to relaunch Meilisearch.

### Activating experimental features during runtime

Some experimental features can be activated via an HTTP call using the [`/experimental-features` API route](/reference/api/experimental_features):

Activating or deactivating experimental features this way does not require you to relaunch Meilisearch.

## Current experimental features | Name | Description | How to configure | | --- | --- | --- | | [Limit task batch size](/learn/self_hosted/configure_meilisearch_at_launch) | Limits number of tasks processed in a single batch | CLI flag or environment variable | | [Log customization](/reference/api/logs) | Customize log output and set up log streams | CLI flag or environment variable, API route | | [Metrics API](/reference/api/metrics) | Exposes Prometheus-compatible analytics data | CLI flag or environment variable, API route | | [Reduce indexing memory usage](/learn/self_hosted/configure_meilisearch_at_launch) | Optimizes indexing performance | CLI flag or environment variable | | [Replication parameters](/learn/self_hosted/configure_meilisearch_at_launch) | Alters task processing for clustering compatibility | CLI flag or environment variable | | [Search queue size](/learn/self_hosted/configure_meilisearch_at_launch) | Configure maximum number of concurrent search requests | CLI flag or environment variable | | [`CONTAINS` filter operator](/learn/filtering_and_sorting/filter_expression_reference#contains) | Enables usage of `CONTAINS` with the `filter` search parameter | API route | | [Edit documents with function](/reference/api/documents#update-documents-with-function) | Use a RHAI function to edit documents directly in the Meilisearch database | API route | | [`/network` route](/reference/api/network) | Enable `/network` route | API route | | [Dumpless upgrade](/learn/self_hosted/configure_meilisearch_at_launch#dumpless-upgrade) | Upgrade Meilisearch without generating a dump | API route | | [Composite embedders](/reference/api/settings#composite-embedders) | Enable composite embedders | API route | | [Search query embedding cache](/learn/self_hosted/configure_meilisearch_at_launch#search-query-embedding-cache) | Enable a cache for search query embeddings | CLI flag or environment variable | | [Uncompressed snapshots](/learn/self_hosted/configure_meilisearch_at_launch#uncompressed-snapshots) | Disable snapshot compaction | CLI flag or environment variable | | [Maximum batch payload size](/learn/self_hosted/configure_meilisearch_at_launch#maximum-batch-payload-size) | Limit batch payload size | CLI flag or environment variable | | [Multimodal search](/reference/api/settings) | Enable multimodal search | API route | | [Disable new indexer](/learn/self_hosted/configure_meilisearch_at_launch) | Use previous settings indexer | CLI flag or environment variable | | [Experimental vector store](/reference/api/settings) | Enables index setting to use experimental vector store | API route | | [Search personalization](/learn/personalization/making_personalized_search_queries) | Enables search personalization | CLI flag or environment variable | ---

## FAQ

## I have never used a search engine before. Can I use Meilisearch anyway?

Of course! No knowledge of ElasticSearch or Solr is required to use Meilisearch.

Meilisearch is really **easy to use** and thus accessible to all kinds of developers.

[Take a quick tour](/learn/self_hosted/getting_started_with_self_hosted_meilisearch) to learn the basics of Meilisearch!

We also provide a lot of tools, including [SDKs](/learn/resources/sdks), to help you integrate easily Meilisearch in your project. We're adding new tools every day!

Plus, you can [contact us](https://discord.meilisearch.com) if you need any help.

## How to know if Meilisearch perfectly fits my use cases?

Since Meilisearch is an open-source and easy-to-use tool, you can give it a try using your data. Follow this [guide](/learn/self_hosted/getting_started_with_self_hosted_meilisearch) to get a quick start!

Besides, we published a [comparison between Meilisearch and other search engines](/learn/resources/comparison_to_alternatives) with the goal of providing an overview of Meilisearch alternatives.

## I am trying to add my documents but I keep receiving a `400 - Bad Request` response

The `400 - Bad request` response often means that your data is not in an expected format. You might have extraneous commas, mismatched brackets, missing quotes, etc. Meilisearch API accepts JSON, CSV, and NDJSON formats.

When [adding or replacing documents](/reference/api/documents#add-or-replace-documents), you must enclose them in an array even if there is only one new document.

## I have uploaded my documents, but I get no result when I search in my index

Your document upload probably failed. To understand why, please check the status of the document addition task using the returned [`taskUid`](/reference/api/tasks#get-one-task). If the task failed, the response should contain an `error` object.

Here is an example of a failed task:

```json
{
 "uid": 1,
 "indexUid": "movies",
 "status": "failed",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 67493,
 "indexedDocuments": 0
 },
 "error": {
 "message": "Document does not have a `:primaryKey` attribute: `:documentRepresentation`.",
 "code": "internal",
 "type": "missing_document_id",
 "link": "https://docs.meilisearch.com/errors#missing-document-id",
 },
 "duration": "PT1S",
 "enqueuedAt": "2021-08-10T14:29:17.000000Z",
 "startedAt": "2021-08-10T14:29:18.000000Z",
 "finishedAt": "2021-08-10T14:29:19.000000Z"
}
```

Check your error message for more information.

## Is killing a Meilisearch process safe?

Killing Meilisearch is **safe**, even in the middle of a process (ex: adding a batch of documents). When you restart the server, it will start the task from the beginning.
More information in the [asynchronous operations guide](/learn/async/asynchronous_operations).

## What are the recommended requirements for hosting a Meilisearch instance?

**The short answer:**

The recommended requirements for hosting a Meilisearch instance will depend on many factors, such as the number of documents, the size of those documents, the number of filters/sorts you will need, and more. For a quick estimate to start with, try to use a machine that has at least ten times the disk space of your dataset.

**The long answer:**

Indexing documents is a complex process, making it difficult to accurately estimate the size and memory use of a Meilisearch database. There are a few aspects to keep in mind when optimizing your instance.

### Memory usage

There are two things that can cause your memory usage (RAM) to spike:

1. Adding documents
2. Updating index settings (if index contains documents)

To reduce memory use and indexing time, follow this best practice: **always update index settings before adding your documents**. This avoids unnecessary double-indexing.

### Disk usage

The following factors have a great impact on the size of your database (in no particular order):

- The number of documents
- The size of documents
- The number of searchable fields
- The number of filterable fields
- The size of each update
- The number of different words present in the dataset

Beware heavily multi-lingual datasets and datasets with many unique words, such as IDs or URLs, as they can slow search speed and greatly increase database size. If you do have ID or URL fields, [make them non-searchable](/reference/api/settings#update-searchable-attributes) unless they are useful as search criteria.

### Search speed

Because Meilisearch uses a [memory map](/learn/engine/storage#lmdb), **search speed is based on the ratio between RAM and database size**. In other words:

- A big database + a small amount of RAM => slow search
- A small database + tons of RAM => lightning fast search

Meilisearch also uses disk space as [virtual memory](/learn/engine/storage#memory-usage). This disk space does not correspond to database size; rather, it provides speed and flexibility to the engine by allowing it to go over the limits of physical RAM.

At this time, the number of CPU cores has no direct impact on index or search speed. However, **the more cores you provide to the engine, the more search queries it will be able to process at the same time**.

#### Speeding up Meilisearch Meilisearch is designed to be fast (≤50ms response time), so speeding it up is rarely necessary. However, if you find that your Meilisearch instance is querying slowly, there are two primary methods to improve search performance:

1. Increase the amount of RAM (or virtual memory)
2. Reduce the size of the database

In general, we recommend the former. However, if you need to reduce the size of your database for any reason, keep in mind that:

- **More relevancy rules => a larger database**
 - The proximity [ranking rule](/learn/relevancy/ranking_rules) alone can be responsible for almost 80% of database size
- Adding many attributes to [`filterableAttributes`](/reference/api/settings#filterable-attributes) also consumes a large amount of disk space
- Multi-lingual datasets are costly, so split your dataset—one language per index
- [Stop words](/reference/api/settings#stop-words) are essential to reducing database size
- Not all attributes need to be [searchable](/learn/relevancy/displayed_searchable_attributes#searchable-fields). Avoid indexing unique IDs.

## Why does Meilisearch send data to Segment? Does Meilisearch track its users?

**Meilisearch will never track or identify individual users**. That being said, we do use Segment to collect anonymous data about user trends, feature usage, and bugs.

You can read more about what metrics we collect, why we collect them, and how to disable it on our [telemetry page](/learn/resources/telemetry). Issues of transparency and privacy are very important to us, so if you feel we are lacking in this area please [open an issue](https://github.com/meilisearch/documentation/issues/new/choose) or send an email to our dedicated email address: [privacy@meilisearch.com](mailto:privacy@meilisearch.com).

---

## Known limitations

Meilisearch has a number of known limitations. Some of these limitations are the result of intentional design trade-offs, while others can be attributed to [LMDB](/learn/engine/storage), the key-value store that Meilisearch uses under the hood.

This article covers hard limits that cannot be altered. Meilisearch also has some default limits that _can_ be changed, such as a [default payload limit of 100MB](/learn/self_hosted/configure_meilisearch_at_launch#payload-limit-size) and a [default search limit of 20 hits](/reference/api/search#limit).

## Maximum Cloud upload size

**Limitation:** The maximum file upload size when using the Cloud interface is 20mb.

**Explanation:** Handling large files may result in degraded user experience and performance issues. To add datasets larger than 20mb to a Cloud project, use the [add documents endpoint](/reference/api/documents#add-or-replace-documents) or [`meilisearch-importer`](https://github.com/meilisearch/meilisearch-importer).

## Maximum number of query words

**Limitation:** The maximum number of terms taken into account for each [search query](/reference/api/search#query-q) is 10. If a search query includes more than 10 words, all words after the 10th will be ignored.

**Explanation:** Queries with many search terms can lead to long response times. This goes against our goal of providing a fast search-as-you-type experience.

## Maximum number of words per attribute

**Limitation:** Meilisearch can index a maximum of 65535 positions per attribute. Any words exceeding the 65535 position limit will be silently ignored.

**Explanation:** This limit is enforced for relevancy reasons. The more words there are in a given attribute, the less relevant the search queries will be.

### Example

Suppose you have three similar queries: `Hello World`, `Hello, World`, and `Hello - World`. Due to how our tokenizer works, each one of them will be processed differently and take up a different number of "positions" in our internal database.

If your query is `Hello World`:

- `Hello` takes the position `0` of the attribute
- `World` takes the position `1` of the attribute

If your query is `Hello, World`:

- `Hello` takes the position `0` of the attribute
- `,` takes the position `8` of the attribute
- `World` takes the position `9` of the attribute

`,` takes 8 positions as it is a hard separator. You can read more about word separators in our [article about data types](/learn/engine/datatypes#string).

If your query is `Hello - World`:

- `Hello` takes the position `0` of the attribute
- `-` takes the position `1` of the attribute
- `World` takes the position `2` of the attribute

`-` takes 1 position as it is a soft separator. You can read more about word separators in our [article about data types](/learn/engine/datatypes#string).

## Maximum number of attributes per document

**Limitation:** Meilisearch can index a maximum of **65,536 attributes per document**. If a document contains more than 65,536 attributes, an error will be thrown.

**Explanation:** This limit is enforced for performance and storage reasons. Overly large internal data structures—resulting from documents with too many fields—lead to overly large databases on disk, and slower search performance.

## Maximum number of documents in an index

**Limitation:** An index can contain no more than 4,294,967,296 documents.

**Explanation:** This is the largest possible value for a 32-bit unsigned integer. Since Meilisearch's engine uses unsigned integers to identify documents internally, this is the maximum number of documents that can be stored in an index.

## Maximum number of concurrent search requests

**Limitation:** Meilisearch handles a maximum of 1000 concurrent search requests.

**Explanation:** This limit exists to prevent Meilisearch from queueing an unlimited number of requests and potentially consuming an unbounded amount of memory. If Meilisearch receives a new request when the queue is already full, it drops a random search request and returns a 503 `too_many_search_requests` error with a `Retry-After` header set to 10 seconds. Configure this limit with [`--experimental-search-queue-size`](/learn/self_hosted/configure_meilisearch_at_launch).

## Length of primary key values

**Limitation:** Primary key values are limited to 511 bytes.

**Explanation:** Meilisearch stores primary key values as LMDB keys, a data type whose size is limited to 511 bytes. If a primary key value exceeds 511 bytes, the task containing these documents will fail.

## Length of individual `filterableAttributes` values

**Limitation:** Individual `filterableAttributes` values are limited to 468 bytes.

**Explanation:** Meilisearch stores `filterableAttributes` values as keys in LMDB, a data type whose size is limited to 511 bytes, to which Meilisearch adds a margin of 44 bytes. Note that this only applies to individual values—e.g., a `genres` attribute can contain any number of values such as `horror`, `comedy`, or `cyberpunk` as long as each one of them is smaller than 468 bytes.

## Maximum filter depth

**Limitation:** searches using the [`filter` search parameter](/reference/api/search#filter) may have a maximum filtering depth of 2000.

**Explanation:** mixing and alternating `AND` and `OR` operators filters creates nested logic structures. Excessive nesting can lead to stack overflow.

### Example

The following filter is composed of a number of filter expressions. Since these statements are all chained with `OR` operators, there is no nesting:

```sql
genre = "romance" OR genre = "horror" OR genre = "adventure"
```

Replacing `OR` with `AND` does not change the filter structure. The following filter's nesting level remains 1:

```sql
genre = "romance" AND genre = "horror" AND genre = "adventure"
```

Nesting only occurs when alternating `AND` and `OR` operators. The following example fetches documents that either belong only to `user` `1`, or belong to users `2` and `3`:

```sql
# AND is nested inside OR, creating a second level of nesting
user = 1 OR user = 2 AND user = 3
```

Adding parentheses can help visualizing nesting depth:

```sql
# Depth 2
user = 1 OR (user = 2 AND user = 3)

# Depth 4
user = 1 OR (user = 2 AND (user = 3 OR (user = 4 AND user = 5)))

# Though this filter is longer, its nesting depth is still 2
user = 1 OR (user = 2 AND user = 3) OR (user = 4 AND user = 5) OR user = 6
```

## Size of integer fields

**Limitation:** Meilisearch can only exactly represent integers between -2⁵³ and 2⁵³.

**Explanation:** Meilisearch stores numeric values as double-precision floating-point numbers. This allows for greater precision and increases the range of magnitudes that Meilisearch can represent, but leads to inaccuracies in [values beyond certain thresholds](https://en.wikipedia.org/wiki/Double-precision_floating-point_format#Precision_limitations_on_integer_values).

## Maximum number of results per search

**Limitation:** By default, Meilisearch returns up to 1000 documents per search.

**Explanation:** Meilisearch limits the maximum amount of returned search results to protect your database from malicious scraping. You may change this by using the `maxTotalHits` property of the [pagination index settings](/reference/api/settings#pagination-object). `maxTotalHits` only applies to the [search route](/reference/api/search) and has no effect on the [get documents with POST](/reference/api/documents#get-documents-with-post) and [get documents with GET](/reference/api/documents#get-documents-with-get) endpoints.

## Large datasets and internal errors

**Limitation:** Meilisearch might throw an internal error when indexing large batches of documents.

**Explanation:** Indexing a large batch of documents, such as a JSON file over 3.5GB in size, can result in Meilisearch opening too many file descriptors. Depending on your machine, this might reach your system's default resource usage limits and trigger an internal error. Use [`ulimit`](https://www.ibm.com/docs/en/aix/7.1?topic=u-ulimit-command) or a similar tool to increase resource consumption limits before running Meilisearch. e.g., call `ulimit -Sn 3000` in a UNIX environment to raise the number of allowed open file descriptors to 3000.

## Maximum database size

**Limitation:** Meilisearch supports a maximum index size of around 80TiB on Linux environments. For performance reasons, Meilisearch recommends keeping indexes under 2TiB.

**Explanation:** Meilisearch can accommodate indexes of any size as long the combined size of active databases is below the maximum virtual address space the OS devotes to a single process. On 64-bit Linux, this limit is approximately 80TiB.

## Maximum task database size

**Limitation:** Meilisearch supports a maximum task database size of 10GiB.

**Explanation:** Depending on your setup, 10GiB should correspond to 5M to 15M tasks. Once the task database contains over 1M entries (roughly 1GiB on average), Meilisearch tries to automatically delete finished tasks while continuing to enqueue new tasks as usual. This ensures the task database does not use an excessive amount of resources. If your database reaches the 10GiB limit, Meilisearch will log a warning indicating the engine is not working properly and refuse to enqueue new tasks.

## Maximum number of indexes in an instance

**Limitation:** Meilisearch can accommodate an arbitrary number of indexes as long as their size does not exceed 2TiB. When dealing with larger indexes, Meilisearch can accommodate up to 20 indexes as long as their combined size does not exceed the OS's virtual address space limit.

**Explanation:** While Meilisearch supports an arbitrary number of indexes under 2TiB, accessing hundreds of different databases in short periods of time might lead to decreased performance and should be avoided when possible.

## Facet Search limitation

**Limitation:** When [searching for facet values](/reference/api/facet_search), Meilisearch returns a maximum of 100 facets.

**Explanation:** the limit to the maximum number of returned facets has been implemented to offer a good balance between usability and comprehensive results. Facet search allows users to filter a large list of facets so they may quickly find categories relevant to their query. This is different from searching through an index of documents. Faceting index settings such as the `maxValuesPerFacet` limit do not impact facet search and only affect queries searching through documents.

---

## Language

Meilisearch is multilingual, featuring optimized support for:

- Any language that uses whitespace to separate words
- Chinese
- Hebrew
- Japanese
- Khmer
- Korean
- Swedish
- Thai

We aim to provide global language support, and your feedback helps us move closer to that goal. If you notice inconsistencies in your search results or the way your documents are processed, please [open an issue in the Meilisearch repository](https://github.com/meilisearch/meilisearch/issues/new/choose).

[Read more about our tokenizer](/learn/indexing/tokenization)

## Improving our language support

While we have employees from all over the world at Meilisearch, we don't speak every language. We rely almost entirely on feedback from external contributors to understand how our engine is performing across different languages.

If you'd like to request optimized support for a language, please upvote the related [discussion in our product repository](https://github.com/meilisearch/product/discussions?discussions_q=label%3Ascope%3Atokenizer+) or [open a new one](https://github.com/meilisearch/product/discussions/new?category=feedback-feature-proposal) if it doesn't exist.

If you'd like to help by developing a tokenizer pipeline yourself: first of all, thank you! We recommend that you take a look at the [tokenizer contribution guide](https://github.com/meilisearch/charabia/blob/main/CONTRIBUTING.md) before making a PR.

## FAQ

### What do you mean when you say Meilisearch offers _optimized_ support for a language?

Optimized support for a language means Meilisearch has implemented internal processes specifically tailored to parsing that language, leading to more relevant results.

### My language does not use whitespace to separate words. Can I still use Meilisearch?

Yes, but search results might be less relevant than in one of the fully optimized languages.

### My language does not use the Roman alphabet. Can I still use Meilisearch?

Yes—our users work with many different alphabets and writing systems, such as Cyrillic, Thai, and Japanese.

### Does Meilisearch plan to support additional languages in the future?

Yes, we definitely do. The more feedback we get from native speakers, the easier it is for us to understand how to improve performance for those languages. Similarly, the more requests we get to improve support for a specific language, the more likely we are to devote resources to that project.

---

## Official SDKs and libraries

Our team and community have worked hard to bring Meilisearch to almost all popular web development languages, frameworks, and deployment options.

New integrations are constantly in development. If you'd like to contribute, [see below](/learn/resources/sdks#contributing).

## SDKs

You can use Meilisearch API wrappers in your favorite language. These libraries support all API routes.

- [.NET](https://github.com/meilisearch/meilisearch-dotnet)
- [Dart](https://github.com/meilisearch/meilisearch-dart)
- [Golang](https://github.com/meilisearch/meilisearch-go)
- [Java](https://github.com/meilisearch/meilisearch-java)
- [JavaScript](https://github.com/meilisearch/meilisearch-js)
- [PHP](https://github.com/meilisearch/meilisearch-php)
- [Python](https://github.com/meilisearch/meilisearch-python)
- [Ruby](https://github.com/meilisearch/meilisearch-ruby)
- [Rust](https://github.com/meilisearch/meilisearch-rust)
- [Swift](https://github.com/meilisearch/meilisearch-swift)

## Framework integrations

- Laravel: the official [Laravel-Scout](https://github.com/laravel/scout) package supports Meilisearch.
- [Ruby on Rails](https://github.com/meilisearch/meilisearch-rails)
- [Symfony](https://github.com/meilisearch/meilisearch-symfony)

## Front-end tools

- [Angular](https://github.com/meilisearch/meilisearch-angular)
- [React](https://github.com/meilisearch/meilisearch-react)
- [Vue](https://github.com/meilisearch/meilisearch-vue)
- [Instant Meilisearch](https://github.com/meilisearch/meilisearch-js-plugins/tree/main/packages/instant-meilisearch)
- [Autocomplete client](https://github.com/meilisearch/meilisearch-js-plugins/tree/main/packages/autocomplete-client)
- [docs-searchbar.js](https://github.com/tauri-apps/meilisearch-docsearch)

## DevOps tools

- [meilisearch-kubernetes](https://github.com/meilisearch/meilisearch-kubernetes)

## Platform plugins

- [VuePress plugin](https://github.com/meilisearch/vuepress-plugin-meilisearch)
- [Strapi plugin](https://github.com/meilisearch/strapi-plugin-meilisearch/)
- [Gatsby plugin](https://github.com/meilisearch/gatsby-plugin-meilisearch/)
- [Firebase](https://github.com/meilisearch/firestore-meilisearch)

## AI Assistant tools

- [meilisearch-mcp](https://github.com/meilisearch/meilisearch-mcp): Model Context Protocol server for integrating Meilisearch with AI assistants and tools
 - Guide: [Model Context Protocol integration](/guides/ai/mcp)

## Other tools

- [docs-scraper](https://github.com/meilisearch/docs-scraper): a scraper tool to automatically read the content of your documentation and store it into Meilisearch.

## Contributing

If you want to build a new integration for Meilisearch, you are more than welcome to and we would be happy to help you!

We are proud that some of our libraries were developed and are still maintained by external contributors! ♥️

We recommend to follow [these guidelines](https://github.com/meilisearch/integrations-guides) so that it will be easier to integrate your work.

---

## Telemetry

Meilisearch collects anonymized data from users to improve our product. This can be [deactivated at any time](#how-to-disable-data-collection), and any data that has already been collected can be [deleted on request](#how-to-delete-all-collected-data).

## What tools do we use to collect and visualize data?

We use [Segment](https://segment.com/), a platform for data collection and management, to collect usage data. We then feed that data into [Amplitude](https://amplitude.com/), a tool for graphing and highlighting data, so that we can build visualizations according to our needs.

## What kind of data do we collect?

Our data collection is focused on the following categories:

- **System** metrics, such as the technical specs of the device running Meilisearch, the software version, and the OS
- **Performance** metrics, such as the success rate of search requests and the average latency
- **Usage** metrics, aimed at evaluating our newest features. These change with each new version

See below for the [complete list of metrics we currently collect](#exhaustive-list-of-all-collected-data).

**We will never:**

- Identify or track users
- Collect personal information such as IP addresses, email addresses, or website URLs
- Store data from documents added to a Meilisearch instance

## Why collect telemetry data?

We collect telemetry data for only two reasons: so that we can improve our product, and so that we can continue working on this project full-time.

to create a better product, we need reliable quantitative information. The data we collect helps us fix bugs, evaluate the success of features, and better understand our users' needs.

We also need to prove that people are actually using Meilisearch. Usage metrics help us justify our existence to investors so that we can keep this project alive.

## Why should you trust us?

**Don't trust us—hold us accountable.** We feel that it is understandable, and in fact wise, to be distrustful of tech companies when it comes to your private data. i.e. why we attempt to maintain [complete transparency about our data collection](#exhaustive-list-of-all-collected-data), provide an [opt-out](#how-to-disable-data-collection), and enable users to [request the deletion of all their collected data](#how-to-delete-all-collected-data) at any time. In the absence of global data protection laws, we believe that this is the only ethical way to approach data collection.

No company is perfect. If you ever feel that we are being anything less than 100% transparent or collecting data i.e. infringing on your personal privacy, please let us know by emailing our dedicated account: [privacy@meilisearch.com](mailto:privacy@meilisearch.com). Similarly, if you discover a data rights initiative or data protection tool that you think is relevant to us, please share it. We are passionate about this subject and take it very seriously.

## How to disable data collection

Data collection can be disabled at any time by setting a command-line option or environment variable, then restarting the Meilisearch instance.

```bash
Meilisearch --no-analytics
```

```bash
export MEILI_NO_ANALYTICS=true
Meilisearch ```

```bash
# First, open /etc/systemd/system/meilisearch.service with a text editor:

nano /etc/systemd/system/meilisearch.service

# Then add --no-analytics at the end of the command in ExecStart
# Don't forget to save and quit!
# Finally, run the following two commands:

systemctl daemon-reload
systemctl restart Meilisearch ```

For more information about configuring Meilisearch, read our [configuration reference](/learn/self_hosted/configure_meilisearch_at_launch).

## How to delete all collected data

We, the Meilisearch team, provide an email address so that users can request the complete removal of their data from all of our tools.

To do so, send an email to [privacy@meilisearch.com](mailto:privacy@meilisearch.com) containing the unique identifier generated for your Meilisearch installation (`Instance UID` when launching Meilisearch). Any questions regarding the management of the data we collect can also be sent to this email address.

## Exhaustive list of all collected data

Whenever an event is triggered that collects some piece of data, Meilisearch does not send it immediately. Instead, it bundles it with other data in a batch of up to `500kb`. Batches are sent either every hour, or after reaching `500kb`—whichever occurs first. This is done to improve performance and reduce network traffic.

This list is liable to change with every new version of Meilisearch. It's not because we're trying to be sneaky! It's because when we add new features we need to collect additional data points to see how they perform. | Metric name | Description | Example |---|---|--- | `context.app.version` | Meilisearch version number | 1.3.0 | `infos.env` | Value of `--env`/`MEILI_ENV` | production | `infos.db_path` | `true` if `--db-path`/`MEILI_DB_PATH` is specified | true | `infos.import_dump` | `true` if `--import-dump` is specified | true | `infos.dump_dir` | `true` if `--dump-dir`/`MEILI_DUMP_DIR` is specified | true | `infos.ignore_missing_dump` | `true` if `--ignore-missing-dump` is activated | true | `infos.ignore_dump_if_db_exists` | `true` if `--ignore-dump-if-db-exists` is activated | true | `infos.import_snapshot` | `true` if `--import-snapshot` is specified | true | `infos.schedule_snapshot` | Value of `--schedule_snapshot`/`MEILI_SCHEDULE_SNAPSHOT` if set, otherwise `None` | 86400 | `infos.snapshot_dir` | `true` if `--snapshot-dir`/`MEILI_SNAPSHOT_DIR` is specified | true | `infos.ignore_missing_snapshot` | `true` if `--ignore-missing-snapshot` is activated | true | `infos.ignore_snapshot_if_db_exists` | `true` if `--ignore-snapshot-if-db-exists` is activated | true | `infos.http_addr` | `true` if `--http-addr`/`MEILI_HTTP_ADDR` is specified | true | `infos.http_payload_size_limit` | Value of `--http-payload-size-limit`/`MEILI_HTTP_PAYLOAD_SIZE_LIMIT` in bytes | 336042103 | `infos.log_level` | Value of `--log-level`/`MEILI_LOG_LEVEL` | debug | `infos.max_indexing_memory` | Value of `--max-indexing-memory`/`MEILI_MAX_INDEXING_MEMORY` in bytes | 336042103 | `infos.max_indexing_threads` | Value of `--max-indexing-threads`/`MEILI_MAX_INDEXING_THREADS` in integer | 4 | `infos.log_level` | Value of `--log-level`/`MEILI_LOG_LEVEL` | debug | `infos.ssl_auth_path` | `true` if `--ssl-auth-path`/`MEILI_SSL_AUTH_PATH` is specified | false | `infos.ssl_cert_path` | `true` if `--ssl-cert-path`/`MEILI_SSL_CERT_PATH` is specified | false | `infos.ssl_key_path` | `true` if `--ssl-key-path`/`MEILI_SSL_KEY_PATH` is specified | false | `infos.ssl_ocsp_path` | `true` if `--ssl-ocsp-path`/`MEILI_SSL_OCSP_PATH` is specified | false | `infos.ssl_require_auth` | Value of `--ssl-require-auth`/`MEILI_SSL_REQUIRE_AUTH` as a boolean | false | `infos.ssl_resumption` | `true` if `--ssl-resumption`/`MEILI_SSL_RESUMPTION` is specified | false | `infos.ssl_tickets` | `true` if `--ssl-tickets`/`MEILI_SSL_TICKETS` is specified | false | `system.distribution` | Distribution on which Meilisearch is launched | Arch Linux | `system.kernel_version` | Kernel version on which Meilisearch is launched | 5.14.10 | `system.cores` | Number of cores | 24 | `system.ram_size` | Total RAM capacity. Expressed in `KB` | 16777216 | `system.disk_size` | Total capacity of the largest disk. Expressed in `Bytes` | 1048576000 | `system.server_provider` | Value of `MEILI_SERVER_PROVIDER` environment variable | AWS | `stats.database_size` | Database size. Expressed in `Bytes` | 2621440 | `stats.indexes_number` | Number of indexes | 2 | `start_since_days` | Number of days since instance was launched | 365 | `user_agent` | User-agent header encountered during API calls | ["Meilisearch Ruby (2.1)", "Ruby (3.0)"] | `requests.99th_response_time` | Highest latency from among the fastest 99% of successful search requests | 57ms | `requests.total_succeeded` | Total number of successful requests | 3456 | `requests.total_failed` | Total number of failed requests | 24 | `requests.total_received` | Total number of received search requests | 3480 | `requests.total_degraded` | Total number of searches canceled after reaching search time cut-off | 100 | `requests.total_used_negative_operator` | Count searches using either a negative word or a negative phrase operator | 173 | `sort.with_geoPoint` | `true` if the sort rule `_geoPoint` is specified | true | `sort.avg_criteria_number` | Average number of sort criteria among all search requests containing the `sort` parameter | 2 | `filter.with_geoBoundingBox` | `true` if the filter rule `_geoBoundingBox` is specified | false | `filter.with_geoRadius` | `true` if the filter rule `_geoRadius` is specified | false | `filter.most_used_syntax` | Most used filter syntax among all search requests containing the `filter` parameter | string | `filter.on_vectors` | `true` if the filter rule includes `_vector` | false | `q.max_terms_number` | Highest number of terms given for the `q` parameter | 5 | `pagination.max_limit` | Highest value given for the `limit` parameter | 60 | `pagination.max_offset` | Highest value given for the `offset` parameter | 1000 | `formatting.max_attributes_to_retrieve` | Maximum number of attributes to retrieve | 100 | `formatting.max_attributes_to_highlight` | Maximum number of attributes to highlight | 100 | `formatting.highlight_pre_tag` | `true` if `highlightPreTag` is specified | false | `formatting.highlight_post_tag` | `true` if `highlightPostTag` is specified | false | `formatting.max_attributes_to_crop` | Maximum number of attributes to crop | 100 | `formatting.crop_length` | `true` if `cropLength` is specified | false | `formatting.crop_marker` | `true` if `cropMarker` is specified | false | `formatting.show_matches_position` | `true` if `showMatchesPosition` is used in this batch | false | `facets.avg_facets_number` | Average number of facets | 10 | `primary_key` | Name of primary key when explicitly set. Otherwise `null` | id | `payload_type` | All values encountered in the `Content-Type` header, including invalid ones | ["application/json", "text/plain", "application/x-ndjson"] | `index_creation` | `true` if a document addition or update request triggered index creation | true | `ranking_rules.words_position` | Position of the `words` ranking rule if any, otherwise `null` | 1 | `ranking_rules.typo_position` | Position of the `typo` ranking rule if any, otherwise `null` | 2 | `ranking_rules.proximity_position` | Position of the `proximity` ranking rule if any, otherwise `null` | 3 | `ranking_rules.attribute_position` | Position of the `attribute` ranking rule if any, otherwise `null` | 4 | `ranking_rules.sort_position` | Position of the `sort` ranking rule | 5 | `ranking_rules.exactness_position` | Position of the `exactness` ranking rule if any, otherwise `null` | 6 | `ranking_rules.values` | A string representing the ranking rules without the custom asc-desc rules | "words, typo, attribute, sort, exactness" | `sortable_attributes.total` | Number of sortable attributes | 3 | `sortable_attributes.has_geo` | `true` if `_geo` is set as a sortable attribute | true | `filterable_attributes.total` | Number of filterable attributes | 3 | `filterable_attributes.has_geo` | `true` if `_geo` is set as a filterable attribute | false | `filterable_attributes.has_patterns` | `true` if `filterableAttributes` uses `attributePatterns` | true | `searchable_attributes.total` | Number of searchable attributes | 4 | `searchable_attributes.with_wildcard` | `true` if `*` is specified as a searchable attribute | false | `per_task_uid` | `true` if a `uids` is used to fetch a particular task resource | true | `filtered_by_uid` | `true` if tasks are filtered by the `uids` query parameter | false | `filtered_by_index_uid` | `true` if tasks are filtered by the `indexUids` query parameter | false | `filtered_by_type` | `true` if tasks are filtered by the `types` query parameter | false | `filtered_by_status` | `true` if tasks are filtered by the `statuses` query parameter | false | `filtered_by_canceled_by` | `true` if tasks are filtered by the `canceledBy` query parameter | false | `filtered_by_before_enqueued_at` | `true` if tasks are filtered by the `beforeEnqueuedAt` query parameter | false | `filtered_by_after_enqueued_at` | `true` if tasks are filtered by the `afterEnqueuedAt` query parameter | false | `filtered_by_before_started_at` | `true` if tasks are filtered by the `beforeStartedAt` query parameter | false | `filtered_by_after_started_at` | `true` if tasks are filtered by the `afterStartedAt` query parameter | false | `filtered_by_before_finished_at` | `true` if tasks are filtered by the `beforeFinishedAt` query parameter | false | `filtered_by_after_finished_at` | `true` if tasks are filtered by the `afterFinishedAt` query parameter | false | `typo_tolerance.enabled` | `true` if typo tolerance is enabled | true | `typo_tolerance.disable_on_attributes` | `true` if at least one value is defined for `disableOnAttributes` | false | `typo_tolerance.disable_on_words` | `true` if at least one value is defined for `disableOnWords` | false | `typo_tolerance.min_word_size_for_typos.one_typo` | The defined value for the `minWordSizeForTypos.oneTypo` parameter | 5 | `typo_tolerance.min_word_size_for_typos.two_typos` | The defined value for the `minWordSizeForTypos.twoTypos` parameter | 9 | `pagination.max_total_hits` | The defined value for the `pagination.maxTotalHits` property | 1000 | `faceting.max_values_per_facet` | The defined value for the `faceting.maxValuesPerFacet` property | 100 | `distinct_attribute.set` | `true` if a field name is specified | false | `distinct` | `true` if a distinct was specified in an aggregated list of requests | true | `proximity_precision.set` | `true` if the setting has been manually set. | false | `proximity_precision.value` | `byWord` or `byAttribute`. | byWord | `facet_search.set` | `facetSearch` has been changed by the user | true | `facet_search.value` | `facetSearch` value set by the user | true | `prefix_search.set` | `prefixSearch` has been changed by the user | true | `prefix_search.value` | `prefixSearch` value set by the user | indexingTime | `displayed_attributes.total` | Number of displayed attributes | 3 | `displayed_attributes.with_wildcard` | `true` if `*` is specified as a displayed attribute | false | `stop_words.total` | Number of stop words | 3 | `separator_tokens.total` | Number of separator tokens | 3 | `non_separator_tokens.total` | Number of non-separator tokens | 3 | `dictionary.total` | Number of words in the dictionary | 3 | `synonyms.total` | Number of synonyms | 3 | `per_index_uid` | `true` if the `uid` is used to fetch an index stat resource | false | `searches.avg_search_count` | The average number of search queries received per call for the aggregated event | 4.2 | `searches.total_search_count` | The total number of search queries received for the aggregated event | 16023 | `indexes.avg_distinct_index_count` | The average number of queried indexes received per call for the aggregated event | 1.2 | `indexes.total_distinct_index_count` | The total number of distinct index queries for the aggregated event | 6023 | `indexes.total_single_index` | The total number of calls when only one index is queried | 2007 | `matching_strategy.most_used_strategy` | Most used word matching strategy | last | `infos.with_configuration_file` | `true` if the instance is launched with a configuration file | false | `infos.experimental_composite_embedders` | `true` if the `compositeEmbedders` feature is set to `true` for this instance | false | `infos.experimental_contains_filter` | `true` if the `containsFilter` experimental feature is enabled | false | `infos.experimental_edit_documents_by_function` | `true` if the `editDocumentsByFunction` experimental feature is enabled | false | `infos.experimental_enable_metrics` | `true` if `--experimental-enable-metrics` is specified at launch | false | `infos.experimental_embedding_cache_entries` | Size of configured embedding cache | 100 | `infos.experimental_multimodal` | `true` when multimodal search feature is enabled | true | | `infos.experimental_no_edition_2024_for_settings` | `true` if instance disabled new indexer | false | `infos.experimental_replication_parameters` | `true` if `--experimental-replication-parameters` is specified at launch | false | `infos.experimental_reduce_indexing_memory_usage` | `true` if `--experimental-reduce-indexing-memory-usage` is specified at launch | false | `infos.experimental_logs_mode` | `human` or `json` depending on the value specified | human | `infos.experimental_enable_logs_route` | `true` if `--experimental-enable-logs-route` is specified at launch | false | `infos.gpu_enabled` | `true` if Meilisearch was compiled with CUDA support | false | `swap_operation_number` | Number of swap operations | 2 | `pagination.most_used_navigation` | Most used search results navigation | estimated | `per_document_id` | `true` if the `DELETE /indexes/:indexUid/documents/:documentUid` endpoint was used | false | `per_filter` | `true` if `POST /indexes/:indexUid/documents/fetch`, `GET /indexes/:indexUid/documents/`, or `POST /indexes/:indexUid/documents/delete` endpoints were used | false | `clear_all` | `true` if `DELETE /indexes/:indexUid/documents` endpoint was used | false | `per_batch` | `true` if the `POST /indexes/:indexUid/documents/delete-batch` endpoint was used | false | `facets.total_distinct_facet_count` | Total number of distinct facets queried for the aggregated event | false | `facets.additional_search_parameters_provided` | `true` if additional search parameters were provided for the aggregated event | false | `faceting.sort_facet_values_by_star_count` | `true` if all fields are set to be sorted by count | false | `faceting.sort_facet_values_by_total` | The number of different values that were set | 10 | `scoring.show_ranking_score` | `true` if `showRankingScore` used in the aggregated event | true | `scoring.show_ranking_score_details` | `true` if `showRankingScoreDetails` was used in the aggregated event | true | `scoring.ranking_score_threshold` | `true` if rankingScoreThreshold was specified in an aggregated list of requests | true | `attributes_to_search_on.total_number_of_uses` | Total number of queries where `attributesToSearchOn` is set | 5 | `vector.max_vector_size` | Highest number of dimensions given for the `vector` parameter in this batch | 1536 | `vector.retrieve_vectors` | `true` if the retrieve_vectors parameter has been used in this batch. | false | `hybrid.enabled` | `true` if hybrid search been used in the aggregated event | true | `hybrid.semantic_ratio` | `true` if semanticRatio was used in this batch, otherwise false | false | `hybrid.total_media` | Aggregated number of search requests where `media` is not `null` | 42 | `embedders.total` | Numbers of defined embedders | 2 | `embedders.sources` | An array representing the different provided sources | ["huggingFace", "userProvided"] | `embedders.document_template_used` | A boolean indicating if one of the provided embedders has a custom template defined | true | `embedders.document_template_max_bytes` | A value indicating the largest value for document TemplateMaxBytes across all embedder | 400 | `embedders.binary_quantization_used` | `true` if the user updated the binary quantized field of the embedded settings | false | `infos.task_queue_webhook` | `true` if the instance is launched with a task queue webhook | false | `infos.experimental_search_queue_size` | Size of the search queue | 750 | `infos.experimental_dumpless_upgrade` | `true` if instance is launched with the parameter | true | `locales` | List of locales used with `/search` and `/settings` routes | ["fra", "eng"] | `federation.use_federation` | `true` when at least one multi-search request contains a top-level federation object | false | `network_has_self` | `true` if the network object has a non-null self field | true | `network_size` | Number of declared remotes | 0 | `network` | `true` when the network experimental feature is enabled | true | `experimental_network` | `true` when the network experimental feature is enabled | true | `remotes.total_distinct_remote_count` | Sum of the number of distinct remotes appearing in each search request of the aggregate | 48 | `remotes.avg_distinct_remote_count` | Average number of distinct remotes appearing in a search request of the aggregate | 2.33 | `multimodal` | `true` when multimodal search is enabled via the `/experimental-features` route | true | `export.total_received` | Number of exports received in this batch | `152` | `export.has_api_key` | Number of exports with an API Key set | `89` | `export.avg_index_patterns` | Average number of index patterns set per export | `3.2` | `export.avg_patterns_with_filter` | Average number of index patterns with filters per export | `1.7` | `export.avg_payload_size` | Average payload size per export | `512` | `webhooks_created` | Number of webhooks created in an instance | `2` | `webhooks.updated` | Number of times all webhooks in an instance have been updated | `5` | `with_vector_filter` | `true` when a document fetch request used a vector filter | `false`

---

## Versioning policy

This article describes the system behind Meilisearch's version numbering, compatibility between Meilisearch versions, and how Meilisearch version numbers relate to SDK and documentation versions.

## Engine versioning

Release versions follow the MAJOR.MINOR.PATCH format and adhere to the [Semantic Versioning 2.0.0 convention](https://semver.org/#semantic-versioning-200).

- MAJOR versions contain changes that break compatibility between releases
- MINOR versions introduce new features that are backwards compatible
- PATCH versions only contain high-priority bug fixes and security updates

Prior to Meilisearch v1, MINOR versions also broke compatibility between releases.

### Release schedule

Meilisearch releases new versions between four and six times a year. This number does not include PATCH releases.

### Support for previous versions

Meilisearch only maintains the latest engine release. Currently, there are no EOL (End of Life) or LTS (Long-Term Support) policies.

Consult the [engine versioning policy](https://github.com/meilisearch/engine-team/blob/main/resources/versioning-policy.md) for more information.

## SDK versioning

Meilisearch version numbers have no relationship to SDK version numbers. e.g., `meilisearch-go` v0.22 introduced compatibility with Meilisearch v0.30. SDKs follow their own release schedules and must address issues beyond compatibility with Meilisearch.

When using an SDK, always consult its repository README, release description, and any dedicated documentation to determine which Meilisearch versions and features it supports.

## Documentation versioning

This Meilisearch documentation website follows the latest Meilisearch version. We do not maintain documentation for past releases.

It is possible to [access previous versions of the Meilisearch documentation website](/learn/update_and_migration/previous_docs_version), but the process and results are less than ideal. Users are strongly encouraged to always use the latest Meilisearch release.

---

## Securing your project

import CodeSamplesBasicSecurityTutorialAdmin1 from '/snippets/samples/code_samples_basic_security_tutorial_admin_1.mdx';
import CodeSamplesBasicSecurityTutorialListing1 from '/snippets/samples/code_samples_basic_security_tutorial_listing_1.mdx';
import CodeSamplesBasicSecurityTutorialSearch1 from '/snippets/samples/code_samples_basic_security_tutorial_search_1.mdx';

This tutorial will show you how to secure your Meilisearch project. You will see how to manage your master key and how to safely send requests to the Meilisearch API using an API key.

## Creating the master key

The master key is the first and most important step to secure your Meilisearch project.

### Creating the master key in Cloud

Cloud automatically generates a master key for each project. This means Cloud projects are secure by default.

You can view your master key by visiting your project settings, then clicking "API Keys" on the sidebar:

 <img src="/assets/images/security/01-master-api-keys.png" alt="An interface element named 'API keys' showing obscured security keys including: 'Master key', 'Default Search API Key', and 'Default Admin API Key'" />

### Creating the master key in a self-hosted instance

To protect your self-hosted instance, relaunch it using the `--master-key` command-line option or the `MEILI_MASTER_KEY` environment variable:

```sh
./Meilisearch --master-key="MASTER_KEY"
```

UNIX:

```sh
export MEILI_MASTER_KEY="MASTER_KEY"
./Meilisearch ```

Windows:

```sh
set MEILI_MASTER_KEY="MASTER_KEY"
./Meilisearch ```

The master key must be at least 16-bytes-long and composed of valid UTF-8 characters. Use one of the following tools to generate a secure master key:

- [`uuidgen`](https://www.digitalocean.com/community/tutorials/workflow-command-line-basics-generating-uuids)
- [`openssl rand`](https://www.openssl.org/docs/man1.0.2/man1/rand.html)
- [`shasum`](https://www.commandlinux.com/man-page/man1/shasum.1.html)
- [randomkeygen.com](https://randomkeygen.com/)

Meilisearch will launch as usual. The start up log should include a message informing you the instance is protected:

```
A master key has been set. Requests to Meilisearch won't be authorized unless you provide an authentication key.
```

If you supplied an insecure key, Meilisearch will display a warning and suggest you relaunch your instance with an autogenerated alternative:

```
We generated a new secure master key for you (you can safely use this token):

>> --master-key E8H-DDQUGhZhFWhTq263Ohd80UErhFmLIFnlQK81oeQ <<

Restart Meilisearch with the argument above to use this new and secure master key.
```

## Obtaining API keys

When your project is protected, Meilisearch automatically generates two API keys: `Default Search API Key` and `Default Admin API Key`. API keys are authorization tokens designed to safely communicate with the Meilisearch API.

### Obtaining API keys in Cloud

Find your API keys by visiting your project settings, then clicking "API Keys" on the sidebar:

 <img src="/assets/images/security/01-master-api-keys.png" alt="An interface element named 'API keys' showing three obscured keys: 'Master key', 'Default Search API Key', and 'Default Admin API Key'" />

### Obtaining API keys in a self-hosted instance

Use your master key to query the `/keys` endpoint to view all API keys in your instance:

Only use the master key to manage API keys. Never use the master key to perform searches or other common operations.

Meilisearch's response will include at least the two default API keys:

```json
{
 "results": [
 {
 "name": "Default Search API Key",
 "description": "Use it to search from the frontend",
 "key": "0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33",
 "uid": "123-345-456-987-abc",
 "actions": [
 "search"
 ],
 "indexes": [
 "*"
 ],
 "expiresAt": null,
 "createdAt": "2024-01-25T16:19:53.949636Z",
 "updatedAt": "2024-01-25T16:19:53.949636Z"
 },
 {
 "name": "Default Admin API Key",
 "description": "Use it for anything i.e. not a search operation. Caution! Do not expose it on a public frontend",
 "key": "62cdb7020ff920e5aa642c3d4066950dd1f01f4d",
 "uid": "123-345-456-987-abc",
 "actions": [
 "*"
 ],
 "indexes": [
 "*"
 ],
 "expiresAt": null,
 "createdAt": "2024-01-25T16:19:53.94816Z",
 "updatedAt": "2024-01-25T16:19:53.94816Z"
 }
 ],
 …
}
```

## Sending secure API requests to Meilisearch Now you have your API keys, you can safely query the Meilisearch API. Add API keys to requests using an `Authorization` bearer token header.

Use the `Default Admin API Key` to perform sensitive operations, such as creating a new index:

Then use the `Default Search API Key` to perform search operations in the index you just created:

## Conclusion

You have successfully secured Meilisearch by configuring a master key. You then saw how to access the Meilisearch API by adding an API key to your request's authorization header.

---

## Differences between the master key and API keys

This article explains the main usage differences between the two types of security keys in Meilisearch: master key and API keys.

## Master key

The master key grants full control over an instance and is the only key with access to endpoints for creating and deleting API keys by default. Since the master key is not an API key, it cannot be configured and listed through the `/keys` endpoints.

**Use the master key to create, update, and delete API keys. Do not use it for other operations.**

Consult the [basic security tutorial](/learn/security/basic_security) to learn more about correctly handling your master key.

Exposing the master key can give malicious users complete control over your Meilisearch project. To minimize risks, **only use the master key when managing API keys**.

## API keys

API keys grant access to a specific set of indexes, routes, and endpoints. You can also configure them to expire after a certain date. Use the [`/keys` route](/reference/api/keys) to create, configure, and delete API keys.

**Use API keys for all API operations except API key management.** This includes search, configuring index settings, managing indexes, and adding and updating documents.

In many cases, the default API keys are all you need to safely manage your Meilisearch project. Use the `Default Search API key` for searching, and the `Default Admin API Key` to configure index settings, add documents, and other operations.

---

## Generate a tenant token without a library

import CodeSamplesTenantTokenGuideSearchNoSdk1 from '/snippets/samples/code_samples_tenant_token_guide_search_no_sdk_1.mdx';

Generating tenant tokens without a library is possible, but not recommended. This guide summarizes the necessary steps.

The full process requires you to create a token header, prepare the data payload with at least one set of search rules, and then sign the token with an API key.

## Prepare token header

The token header must specify a `JWT` type and an encryption algorithm. Supported tenant token encryption algorithms are `HS256`, `HS384`, and `HS512`.

```json
{
 "alg": "HS256",
 "typ": "JWT"
}
```

## Build token payload

First, create a set of search rules:

```json
{
 "INDEX_NAME": {
 "filter": "ATTRIBUTE = VALUE"
 }
}
```

Next, find your default search API key. Query the [get an API key endpoint](/reference/api/keys#get-one-key) and inspect the `uid` field to obtain your API key's UID:

```sh
curl \
 -X GET 'MEILISEARCH_URL/keys/API_KEY' \
 -H 'Authorization: Bearer MASTER_KEY'
```

For maximum security, you should also set an expiry date for your tenant tokens. The following Node.js example configures the token to expire 20 minutes after its creation:

```js
parseInt(Date.now() / 1000) + 20 * 60
```

Lastly, assemble all parts of the payload in a single object:

```json
{
 "exp": UNIX_TIMESTAMP,
 "apiKeyUid": "API_KEY_UID",
 "searchRules": {
 "INDEX_NAME": {
 "filter": "ATTRIBUTE = VALUE"
 }
 }
}
```

Consult the [token payload reference](/learn/security/tenant_token_reference) for more information on the requirements for each payload field.

## Encode header and payload

You must then encode both the header and the payload into `base64`, concatenate them, and generate the token by signing it using your chosen encryption algorithm.

## Make a search request using a tenant token

After signing the token, you can use it to make search queries in the same way you would use an API key.

---

## Multitenancy and tenant tokens

import CodeSamplesTenantTokenGuideGenerateSdk1 from '/snippets/samples/code_samples_tenant_token_guide_generate_sdk_1.mdx';
import CodeSamplesTenantTokenGuideSearchSdk1 from '/snippets/samples/code_samples_tenant_token_guide_search_sdk_1.mdx';

There are two steps to use tenant tokens with an official SDK: generating the tenant token, and making a search request using that token.

## Requirements

- a working Meilisearch project
- an application supporting authenticated users
- one of Meilisearch's official SDKs installed

## Generate a tenant token with an official SDK

First, import the SDK. Then create a set of [search rules](/learn/security/tenant_token_reference#search-rules):

```json
{
 "patient_medical_records": {
 "filter": "user_id = 1"
 }
}
```

Search rules must be an object where each key corresponds to an index in your instance. You may configure any number of filters for each index.

Next, find your default search API key. Query the [get an API key endpoint](/reference/api/keys#get-one-key) and inspect the `uid` field to obtain your API key's UID:

```sh
curl \
 -X GET 'MEILISEARCH_URL/keys/API_KEY' \
 -H 'Authorization: Bearer MASTER_KEY'
```

For maximum security, you should also define an expiry date for tenant tokens.

Finally, send this data to your chosen SDK's tenant token generator:

The SDK will return a valid tenant token.

## Make a search request using a tenant token

After creating a token, you must send it your application's front end. Exactly how to do that depends on your specific setup.

Once the tenant token is available, use it to authenticate search requests as if it were an API key:

Applications may use tenant tokens and API keys interchangeably when searching. e.g., the same application might use a default search API key for queries on public indexes and a tenant token for logged-in users searching on private data.

---

## Generate tenant tokens without a Meilisearch SDK

import CodeSamplesTenantTokenGuideSearchNoSdk1 from '/snippets/samples/code_samples_tenant_token_guide_search_no_sdk_1.mdx';

This guide shows you the main steps when creating tenant tokens using [`node-jsonwebtoken`](https://www.npmjs.com/package/jsonwebtoken), a third-party library.

## Requirements

- a working Meilisearch project
- a JavaScript application supporting authenticated users
- `jsonwebtoken` v9.0

## Generate a tenant token with `jsonwebtoken`

### Build the tenant token payload

First, create a set of search rules:

```json
{
 "INDEX_NAME": {
 "filter": "ATTRIBUTE = VALUE"
 }
}
```

Next, find your default search API key. Query the [get an API key endpoint](/reference/api/keys#get-one-key) and inspect the `uid` field to obtain your API key's UID:

```sh
curl \
 -X GET 'MEILISEARCH_URL/keys/API_KEY' \
 -H 'Authorization: Bearer MASTER_KEY'
```

For maximum security, you should also set an expiry date for your tenant tokens. The following example configures the token to expire 20 minutes after its creation:

```js
parseInt(Date.now() / 1000) + 20 * 60
```

### Create tenant token

First, include `jsonwebtoken` in your application. Next, assemble the token payload and pass it to `jsonwebtoken`'s `sign` method:

```js
const jwt = require('jsonwebtoken');

const apiKey = 'API_KEY';
const apiKeyUid = 'API_KEY_UID';
const currentUserID = 'USER_ID';
const expiryDate = parseInt(Date.now() / 1000) + 20 * 60; // 20 minutes

const tokenPayload = {
 searchRules: {
 'INDEX_NAME': {
 'filter': `user_id = ${currentUserID}`
 }
 },
 apiKeyUid: apiKeyUid,
 exp: expiryDate
};

const token = jwt.sign(tokenPayload, apiKey, {algorithm: 'HS256'});
```

`sign` requires the payload, a Meilisearch API key, and an encryption algorithm. Meilisearch supports the following encryption algorithms: `HS256`, `HS384`, and `HS512`.

Your tenant token is now ready to use.

Though this example used `jsonwebtoken`, a Node.js package, you may use any JWT-compatible library in whatever language you feel comfortable.

## Make a search request using a tenant token

After signing the token, you can use it to make search queries in the same way you would use an API key.

---

## Multitenancy and tenant tokens

In this article you'll read what multitenancy is and how tenant tokens help managing complex applications and sensitive data.

## What is multitenancy?

In software development, multitenancy means that multiple users or tenants share the same computing resources with different levels of access to system-wide data. Proper multitenancy is crucial in cloud computing services such as [DigitalOcean's Droplets](https://www.digitalocean.com/products/droplets) and [Amazon's AWS](https://aws.amazon.com/).

If your Meilisearch application stores sensitive data belonging to multiple users in the same index, you are managing a multi-tenant index. In this context, it is very important to make sure users can only search through their own documents. This can be accomplished with **tenant tokens**.

## What is a tenant token?

Tenant tokens are small packages of encrypted data presenting proof a user can access a certain index. They contain not only security credentials, but also instructions on which documents within that index the user is allowed to see. **Tenant tokens only give access to the search endpoints.** They are meant to be short-lived, so Meilisearch does not store nor keep track of generated tokens.

## What is the difference between tenant tokens and API keys?

API keys give general access to specific actions in an index. An API key with search permissions for a given index can access all information in that index.

Tenant tokens add another layer of control over API keys. They can restrict which information a specific user has access to in an index. If you store private data from multiple customers in a single index, tenant tokens allow you to prevent one user from accessing another's data.

## How to integrate tenant tokens with an application?

Tenant tokens do not require any specific Meilisearch configuration. You can use them exactly the same way as you would use any API key with search permissions.

You must generate tokens in your application. The quickest method to generate tenant tokens is [using an official SDK](/learn/security/generate_tenant_token_sdk). It is also possible to [generate a token with a third-party library](/learn/security/generate_tenant_token_third_party).

## Sample application

Meilisearch developed an in-app search demo using multi-tenancy in a SaaS CRM. It only allows authenticated users to search through contacts, companies, and deals belonging to their organization.

Check out this [sample application](https://saas.meilisearch.com/?utm_source=docs) Its code is publicly available in a dedicated [GitHub repository](https://github.com/meilisearch/saas-demo/).

You can also use tenant tokens in role-based access control (RBAC) systems. Consult [How to implement RBAC with Meilisearch](https://blog.meilisearch.com/role-based-access-guide/) on Meilisearch's official blog for more information.

---

## Protected and unprotected Meilisearch projects

This article explains the differences between protected and unprotected Meilisearch projects and instances.

## Protected projects

In protected projects, all Meilisearch API routes and endpoints can only be accessed by requests bearing an API key. The only exception to this rule is the `/health` endpoint, which may still be queried with unauthorized requests.

**Cloud projects are protected by default**. Self-hosted instances are only protected if you launch them with a master key.

Consult the [basic security tutorial](/learn/security/basic_security) for instructions on how to communicate with protected projects.

## Unprotected projects

In unprotected projects and self-hosted instances, any user may access any API endpoint. Never leave a publicly accessible instance unprotected. Only use unprotected instances in safe development environments.

Cloud projects are always protected. Meilisearch self-hosted instances are unprotected by default.

---

## Resetting the master key

This guide shows you how to manage the master key in Cloud and self-hosted instances. Resetting the master key may be necessary if an unauthorized party obtains access to your master key.

## Resetting the master key in Cloud

Cloud does not give users control over the master key. If you need to change your master key, contact support through the Cloud interface or on the official [Meilisearch Discord server](https://discord.meilisearch.com).

Resetting the master key automatically invalidates all API keys. Cloud will generate new default API keys automatically.

## Resetting the master key in self-hosted instances

To reset your master key in a self-hosted instance, relaunch your instance and pass a new value to `--master-key` or `MEILI_MASTER_KEY`.

Resetting the master key automatically invalidates all API keys. Cloud will generate new default API keys automatically.

---

## Tenant token payload reference

Meilisearch's tenant tokens are JSON web tokens (JWTs). Their payload is made of three elements: [search rules](#search-rules), an [API key UID](#api-key-uid), and an optional [expiration date](#expiry-date).

## Example payload

```json
{
 "exp": 1646756934,
 "apiKeyUid": "at5cd97d-5a4b-4226-a868-2d0eb6d197ab",
 "searchRules": {
 "INDEX_NAME": {
 "filter": "attribute = value"
 }
 }
}
```

## Search rules

The search rules object are a set of instructions defining search parameters Meilisearch will enforced in every query made with a specific tenant token.

### Search rules object

`searchRules` must be a JSON object. Each key must correspond to one or more indexes:

```json
{
 "searchRules": {
 "*": {},
 "INDEX_*": {},
 "INDEX_NAME_A": {}
 }
}
```

Each search rule object may contain a single `filter` key. This `filter`'s value must be a [filter expression](/learn/filtering_and_sorting/filter_expression_reference):

```json
{
 "*": {
 "filter": "attribute_A = value_X AND attribute_B = value_Y"
 }
}
```

Meilisearch applies the filter to all searches made with that tenant token. A token only has access to the indexes present in the `searchRules` object.

A token may contain rules for any number of indexes. **Specific rulesets take precedence and overwrite `*` rules.**

Because tenant tokens are generated in your application, Meilisearch cannot check if search rule filters are valid. Invalid search rules return throw errors when searching.

Consult the search API reference for [more information on Meilisearch filter syntax](/reference/api/search#filter).

The search rule may also be an empty object. In this case, the tenant token will have access to all documents in an index:

```json
{
 "INDEX_NAME": {}
}
```

### Examples

#### Single filter

In this example, the user will only receive `medical_records` documents whose `user_id` equals `1`:

```json
{
 "medical_records": {
 "filter": "user_id = 1"
 }
}
```

#### Multiple filters

In this example, the user will only receive `medical_records` documents whose `user_id` equals `1` and whose `published` field equals `true`:

```json
{
 "medical_records": {
 "filter": "user_id = 1 AND published = true"
 }
}
```

#### Give access to all documents in an index

In this example, the user has access to all documents in `medical_records`:

```json
{
 "medical_records": {}
}
```

#### Target multiple indexes with a partial wildcard

In this example, the user will receive documents from any index starting with `medical`. This includes indexes such as `medical_records` and `medical_patents`:

```json
{
 "medical*": {
 "filter": "user_id = 1"
 }
}
```

#### Target all indexes with a wildcard

In this example, the user will receive documents from any index in the whole instance:

```json
{
 "*": {
 "filter": "user_id = 1"
 }
}
```

### Target multiple indexes manually

In this example, the user has access to documents with `user_id = 1` for all indexes, except one. When querying `medical_records`, the user will only have access to published documents:

```json
{
 "*": {
 "filter": "user_id = 1"
 },
 "medical_records": {
 "filter": "user_id = 1 AND published = true",
 }
}
```

## API key UID

Tenant token payloads must include an API key UID to validate requests. The UID is an alphanumeric string identifying an API key:

```json
{
 "apiKeyUid": "at5cd97d-5a4b-4226-a868-2d0eb6d197ab"
}
```

Query the [get one API key endpoint](/reference/api/keys) to obtain an API key's UID.

The UID must indicate an API key with access to [the search action](/reference/api/keys#actions). A token has access to the same indexes and routes as the API key used to generate it.

Since a master key is not an API key, **you cannot use a master key to create a tenant token**. Avoid exposing API keys and **always generate tokens on your application's back end**.

If an API key expires, any tenant tokens created with it will become invalid. The same applies if the API key is deleted or regenerated due to a changed master key.

## Expiry date

The expiry date must be a UNIX timestamp or `null`:

```json
{
 "exp": 1646756934
}
```

A token's expiration date cannot exceed its parent API key's expiration date.

Setting a token expiry date is optional, but highly recommended. Tokens without an expiry date remain valid indefinitely and may be a security liability.

The only way to revoke a token without an expiry date is to [delete](/reference/api/keys#delete-a-key) its parent API key.

Changing an instance's master key forces Meilisearch to regenerate all API keys and will also render all existing tenant tokens invalid.

---

## Multitenancy and tenant tokens

import CodeSamplesTenantTokenGuideGenerateSdk1 from '/snippets/samples/code_samples_tenant_token_guide_generate_sdk_1.mdx';
import CodeSamplesTenantTokenGuideSearchNoSdk1 from '/snippets/samples/code_samples_tenant_token_guide_search_no_sdk_1.mdx';
import CodeSamplesTenantTokenGuideSearchSdk1 from '/snippets/samples/code_samples_tenant_token_guide_search_sdk_1.mdx';

In this guide you'll first learn what multitenancy is and how tenant tokens help managing complex applications and sensitive data. Then, you'll see how to generate and use tokens, whether with an official SDK or otherwise. The guide ends with a quick explanation of the main tenant token settings.

Tenant tokens are generated by using API keys. This article may be easier to follow if you have already read the [security tutorial](/learn/security/basic_security) and [API keys guide](/learn/security/basic_security).

You can also use tenant tokens in role-based access control (RBAC) systems. Consult [How to implement RBAC with Meilisearch](https://blog.meilisearch.com/role-based-access-guide/) on Meilisearch's official blog for more information.

## What is multitenancy?

In software development, multitenancy means that multiple users—also called tenants—share the same computing resources with different levels of access to system-wide data. Proper multitenancy is crucial in cloud computing services such as [DigitalOcean's Droplets](https://www.digitalocean.com/products/droplets) and [Amazon's AWS](https://aws.amazon.com/).

If your Meilisearch application stores sensitive data belonging to multiple users in the same index, we can say it is a multi-tenant index. In this context, it is very important to make sure users can only search through their own documents. This can be accomplished with **tenant tokens**.

### What are tenant tokens and how are they different from API keys in Meilisearch?

Tenant tokens are small packages of encrypted data presenting proof a user can access a certain index. They contain not only security credentials, but also instructions on which documents within that index the user is allowed to see. **Tenant tokens only give access to the search endpoints.**

To use tokens in Meilisearch, you only need to have a system for token generation in place. The quickest method to generate tenant tokens is [using one of our official SDKs](#generating-tenant-tokens-with-an-sdk). It is also possible to [generate a token from scratch](#generating-tenant-tokens-without-a-meilisearch-sdk).

Tenant tokens do not require you to configure any specific [instance options](/learn/self_hosted/configure_meilisearch_at_launch) or [index settings](/reference/api/settings). They are also meant to be short-lived—Meilisearch does not store nor keeps track of generated tokens.

## Generating tenant tokens with an SDK

Imagine that you are developing an application that allows patients and doctors to search through medical records. In your application, it is crucial that each patient can see only their own records and not those of another patient.

The code in this example imports the SDK, creates a filter based on the current user's ID, and feeds that data into the SDK's `generateTenantToken` function. Once the token is generated, it is stored in the `token` variable:

There are three important parameters to keep in mind when using an SDK to generate a tenant token: **search rules**, **API key**, and **expiration date**. Together, they make the token's payload.

**Search rules** must be a JSON object specifying the restrictions that will be applied to search requests on a given index. It must contain at least one search rule. [To learn more about search rules, take a look at our tenant token payload reference.](#search-rules)

As its name indicates, **API key** must be a valid Meilisearch API key with access to [the search action](/reference/api/keys#actions). A tenant token will have access to the same indexes as the API key used when generating it. If no API key is provided, the SDK might be able to infer it automatically.

**Expiration date** is optional when using an SDK. Tokens become invalid after their expiration date. Tokens without an expiration date will expire when their parent API key does.

You can read more about each element of a tenant token payload in [this guide's final section](#tenant-token-payload-reference).

### Using a tenant token with an SDK

After creating a token, you can send it back to the front-end. There, you can use it to make queries that will only return results whose `user_id` attribute equals the current user's ID:

Applications may use tenant tokens and API keys interchangeably when searching. e.g., the same application might use a default search API key for queries on public indexes and a tenant token for logged-in users searching on private data.

## Generating tenant tokens without a Meilisearch SDK

Though Meilisearch recommends [using an official SDK to generate tenant tokens](#generating-tenant-tokens-with-an-sdk), this is not a requirement. Since tenant tokens follow the [JWT standard](https://jwt.io), you can use a number of [compatible third-party libraries](https://jwt.io/libraries). You may also skip all assistance and generate a token from scratch, though this is probably unnecessary in most production environments.

If you are already familiar with the creation of JWTs and only want to know about the specific requirements of a tenant token payload, skip this section and take a look at the [token payload reference](#tenant-token-payload-reference).

### Generating a tenant token with a third-party library

Using a third-party library for tenant token generation is fairly similar to creating tokens with an official SDK. The following example uses the [`node-jsonwebtoken`](https://github.com/auth0/node-jsonwebtoken) library:

```js
const jwt = require('jsonwebtoken');

const apiKey = 'my_api_key';
const apiKeyUid = 'ac5cd97d-5a4b-4226-a868-2d0eb6d197ab';
const currentUserID = 'a_user_id';

const tokenPayload = {
 searchRules: {
 'patient_medical_records': {
 'filter': `user_id = ${currentUserID}`
 }
 },
 apiKeyUid: apiKeyUid,
 exp: parseInt(Date.now() / 1000) + 20 * 60 // 20 minutes
};

const token = jwt.sign(tokenPayload, apiKey, {algorithm: 'HS256'});
```

`tokenPayload` contains the token payload. It must contain three fields: `searchRules`, `apiKeyUid`, and `exp`.

`searchRules` must be a JSON object containing a set of search rules. These rules specify restrictions applied to every query using this web token.

`apiKeyUid` must be the `uid` of a valid Meilisearch API key.

`exp` is the only optional parameter of a tenant token. It must be a UNIX timestamp specifying the expiration date of the token.

For more information on each one of the tenant token fields, consult the [token payload reference](#tenant-token-payload-reference).

`tokenPayload` is passed to `node-jsonwebtoken`'s `sign` method, together with the complete API key used in the payload and the chosen encryption algorithm. Meilisearch supports the following encryption algorithms: `HS256`, `HS384`, and `HS512`.

Though this example used `node-jsonwebtoken`, a NodeJS package, you may use any JWT-compatible library in whatever language you feel comfortable.

After signing the token, you can use it to make search queries in the same way you would use an API key.

The `curl` example presented here is only for illustration purposes. In production environments, you would likely send the token to the front-end of your application and query indexes from there.

### Generating a tenant token from scratch

Generating tenant tokens without a library is possible, but requires considerably more effort.

Though creating a JWT from scratch is out of scope for this guide, here's a quick summary of the necessary steps.

The full process requires you to create a token header, prepare the data payload with at least one set of search rules, and then sign the token with an API key.

The token header must specify a `JWT` type and an encryption algorithm. Supported tenant token encryption algorithms are `HS256`, `HS384`, and `HS512`.

```json
{
 "alg": "HS256",
 "typ": "JWT"
}
```

The token payload contains most of the relevant token data. It must be an object containing a set of search rules and the first 8 characters of a Meilisearch API key. You may optionally set an expiration date for your token. Consult the [token payload reference](#tenant-token-payload-reference) for more information on the requirements for each payload field.

```json
{
 "exp": 1646756934,
 "apiKeyUid": "ac5cd97d-5a4b-4226-a868-2d0eb6d197ab",
 "searchRules": {
 "patient_medical_records": {
 "filter": "user_id = 1"
 }
 }
}
```

You must then encode both the header and the payload into `base64`, concatenate them, and finally generate the token by signing it using your chosen encryption algorithm.

Once your token is ready, it can seamlessly replace API keys to authorize requests made to the search endpoint:

The `curl` example presented here is only for illustration purposes. In production environments, you would likely send the token to the front-end of your application and query indexes from there.

## Tenant token payload reference

Meilisearch's tenant tokens are JWTs. Their payload is made of three elements: [search rules](#search-rules), an [API key](#api-key), and an optional [expiration date](#expiry-date).

You can see each one of them assigned to its own variable in this example:

### Search rules

Search rules are a set of instructions defining search parameters that will be enforced in every query made with a specific tenant token.

`searchRules` must contain a JSON object specifying rules that will be enforced on any queries using this token. Each rule is itself a JSON object and must follow this pattern:

```json
{
 "[index_name]": {
 "[search_parameter]": "[value]"
 }
}
```

The object key must be an index name. You may use the `*` wildcard instead of a specific index name—in this case, search rules will be applied to all indexes.

The object value must consist of `search_parameter:value` pairs. Currently, **tenant tokens only support the `filter` [search parameter](/reference/api/search#filter)**.

In this example, all queries across all indexes will only return documents whose `user_id` equals `1`:

```json
{
 "*": {
 "filter": "user_id = 1"
 }
}
```

You can also use the `*` wildcard by adding it at the end of a string. This allows the tenant token to access all index names starting with that string.

The following example queries across all indexes starting with the string `medical` (like `medical_records`) and returns documents whose `user_id` equals `1`:

```json
{
 "medical*": {
 "filter": "user_id = 1 AND published = true"
 }
}
```

The next rule goes a bit further. When searching on the `patient_medical_records` index, a user can only see records that belong to them and have been marked as published:

```json
{
 "patient_medical_records": {
 "filter": "user_id = 1 AND published = true"
 }
}
```

A token may contain rules for any number of indexes. **Specific rulesets take precedence and overwrite `*` rules.**

The previous rules can be combined in one tenant token:

```json
{
 "apiKeyUid": "ac5cd97d-5a4b-4226-a868-2d0eb6d197ab",
 "exp": 1641835850,
 "searchRules": {
 "*": {
 "filter": "user_id = 1"
 },
 "medical_records": {
 "filter": "user_id = 1 AND published = true",
 }
 }
}
```

Because tenant tokens are generated in your application, Meilisearch cannot check if search rule filters are valid. Invalid search rules will only throw errors when they are used in a query.

Consult the search API reference for [more information on Meilisearch filter syntax](/reference/api/search#filter).

### API key

Creating a token requires an API key with access to [the search action](/reference/api/keys#actions). A token has access to the same indexes and routes as the API key used to generate it.

Since a master key is not an API key, **you cannot use a master key to create a tenant token**.

For security reasons, we strongly recommend you avoid exposing the API key whenever possible and **always generate tokens on your application's back-end**.

When using an official Meilisearch SDK, you may indicate which API key you wish to use when generating a token. Consult the documentation of the SDK you are using for more specific instructions.

If an API key expires, any tenant tokens created with it will become invalid. The same applies if the API key is deleted or regenerated due to a changed master key.

[You can read more about API keys in the API reference.](/reference/api/keys)

### Expiry date

It is possible to define an expiry date when generating a token. This is good security practice and Meilisearch recommends setting relatively short token expiry dates whenever possible.

The expiry date must be a UNIX timestamp or `null`. Additionally, a token's expiration date cannot exceed its parent API key's expiration date. e.g., if an API key is set to expire on 2022-10-15, a token generated with that API key cannot be set to expire on 2022-10-16.

Setting a token expiry date is optional, but recommended. A token without an expiry date never expires and can be used indefinitely as long as its parent API key remains valid.

The only way to revoke a token without an expiry date is to [delete](/reference/api/keys#delete-a-key) its parent API key.

Changing an instance's master key forces Meilisearch to regenerate all API keys and will also render all existing tenant tokens invalid.

When using an official Meilisearch SDK, you may indicate the expiry date when generating a token. Consult the documentation of the SDK you are using for more specific instructions.

## Example application

Our in-app search demo implements multi-tenancy in a SaaS (Software as a Service) CRM. It only allows authenticated users to search through contacts, companies, and deals belonging to their organization.

Check out the [SaaS demo](https://saas.meilisearch.com) and the [GitHub repository](https://github.com/meilisearch/saas-demo/).

---

## Configure Meilisearch at launch

import { NoticeTag } from '/snippets/notice_tag.mdx';

When self-hosting Meilisearch, you can configure your instance at launch with **command-line options**, **environment variables**, or a **configuration file**.

These startup options affect your entire Meilisearch instance, not just a single index. For settings that affect search within a single index, see [index settings](/reference/api/settings).

## Command-line options and flags

Pass **command-line options** and their respective values when launching a Meilisearch instance.

```bash
./Meilisearch --db-path ./meilifiles --http-addr 'localhost:7700'
```

In the previous example, `./meilisearch` is the command that launches a Meilisearch instance, while `--db-path` and `--http-addr` are options that modify this instance's behavior.

Meilisearch also has a number of **command-line flags.** Unlike command-line options, **flags don't take values**. If a flag is given, it is activated and changes Meilisearch's default behavior.

```bash
./Meilisearch --no-analytics
```

The above flag disables analytics for the Meilisearch instance and does not accept a value.

**Both command-line options and command-line flags take precedence over environment variables.** All command-line options and flags are prepended with `--`.

## Environment variables

To configure a Meilisearch instance using environment variables, set the environment variable prior to launching the instance. If you are unsure how to do this, read more about [setting and listing environment variables](https://linuxize.com/post/how-to-set-and-list-environment-variables-in-linux/), or [use a command-line option](#command-line-options-and-flags) instead.

```sh
export MEILI_DB_PATH=./meilifiles
export MEILI_HTTP_ADDR=localhost:7700
./Meilisearch ```

```sh
set MEILI_DB_PATH=./meilifiles
set MEILI_HTTP_ADDR=127.0.0.1:7700
./Meilisearch ```

In the previous example, `./meilisearch` is the command that launches a Meilisearch instance, while `MEILI_DB_PATH` and `MEILI_HTTP_ADDR` are environment variables that modify this instance's behavior.

Environment variables for command-line flags accept `n`, `no`, `f`, `false`, `off`, and `0` as `false`. An absent environment variable will also be considered as `false`. Any other value is considered `true`.

Environment variables are always identical to the corresponding command-line option, but prepended with `MEILI_` and written in all uppercase.

## Configuration file

Meilisearch accepts a configuration file in the `.toml` format as an alternative to command-line options and environment variables. Configuration files can be easily shared and versioned, and allow you to define multiple options.

**When used simultaneously, environment variables override the configuration file, and command-line options override environment variables.**

You can download a default configuration file using the following command:

```sh
curl https://raw.githubusercontent.com/meilisearch/meilisearch/latest/config.toml > config.toml
```

By default, Meilisearch will look for a `config.toml` file in the working directory. If it is present, it will be used as the configuration file. You can verify this when you launch Meilisearch:

```
888b d888 d8b 888 d8b 888
8888b d8888 Y8P 888 Y8P 888
88888b.d88888 888 888
888Y88888P888 .d88b. 888 888 888 .d8888b .d88b. 8888b. 888d888 .d8888b 88888b.
888 Y888P 888 d8P Y8b 888 888 888 88K d8P Y8b "88b 888P" d88P" 888 "88b
888 Y8P 888 88888888 888 888 888 "Y8888b. 88888888 .d888888 888 888 888 888
888 " 888 Y8b. 888 888 888 X88 Y8b. 888 888 888 Y88b. 888 888
888 888 "Y8888 888 888 888 88888P' "Y8888 "Y888888 888 "Y8888P 888 888

Config file path: "./config.toml"
```

If the `Config file path` is anything other than `"none"`, it means that a configuration file was successfully located and used to start Meilisearch.

You can override the default location of the configuration file using the `MEILI_CONFIG_FILE_PATH` environment variable or the `--config-file-path` CLI option:

```sh
./Meilisearch --config-file-path="./config.toml"
```

UNIX:

```sh
export MEILI_CONFIG_FILE_PATH="./config.toml"
./Meilisearch ```

Windows:

```sh
set MEILI_CONFIG_FILE_PATH="./config.toml"
./Meilisearch ```

### Configuration file formatting

You can configure any environment variable or CLI option using a configuration file. In configuration files, options must be written in [snake case](https://en.wikipedia.org/wiki/Snake_case). e.g., `--import-dump` would be written as `import_dump`.

```toml
import_dump = "./example.dump"
```

Specifying the `config_file_path` option within the configuration file will throw an error. This is the only configuration option that cannot be set within a configuration file.

## Configuring cloud-hosted instances

To configure Meilisearch with command-line options in a cloud-hosted instance, edit its [service file](/guides/running_production#step-4-run-meilisearch-as-a-service). The default location of the service file is `/etc/systemd/system/meilisearch.service`.

To configure Meilisearch with environment variables in a cloud-hosted instance, modify Meilisearch's `env` file. Its default location is `/var/opt/meilisearch/env`.

After editing your configuration options, relaunch the Meilisearch service:

```sh
systemctl restart Meilisearch ```

[Cloud](https://www.meilisearch.com/cloud?utm_campaign=oss&utm_source=docs&utm_medium=instance-options) offers an optimal pre-configured environment. You do not need to use any of the configuration options listed in this page when hosting your project on Cloud.

## All instance options

### Configuration file path

**Environment variable**: `MEILI_CONFIG_FILE_PATH`<br/>
**CLI option**: `--config-file-path`<br/>
**Default**: `./config.toml`<br/>
**Expected value**: a filepath

Designates the location of the configuration file to load at launch.

Specifying this option in the configuration file itself will throw an error (assuming Meilisearch is able to find your configuration file).

### Database path

**Environment variable**: `MEILI_DB_PATH`<br />
**CLI option**: `--db-path`<br />
**Default value**: `"data.ms/"`<br />
**Expected value**: a filepath

Designates the location where database files will be created and retrieved.

### Environment

**Environment variable**: `MEILI_ENV`<br />
**CLI option**: `--env`<br />
**Default value**: `development`<br />
**Expected value**: `production` or `development`

Configures the instance's environment. Value must be either `production` or `development`.

`production`:

- Setting a [master key](/learn/security/basic_security) of at least 16 bytes is **mandatory**. If no master key is provided or if it is under 16 bytes, Meilisearch will suggest a secure autogenerated master key
- The [search preview interface](/learn/getting_started/search_preview) is disabled

`development`:

- Setting a [master key](/learn/security/basic_security) is **optional**. If no master key is provided or if it is under 16 bytes, Meilisearch will suggest a secure autogenerated master key
- Search preview is enabled

When the server environment is set to `development`, providing a master key is not mandatory. This is useful when debugging and prototyping, but dangerous otherwise since API routes are unprotected.

### HTTP address & port binding

**Environment variable**: `MEILI_HTTP_ADDR`<br />
**CLI option**: `--http-addr`<br />
**Default value**: `"localhost:7700"`<br />
**Expected value**: an HTTP address and port

Sets the HTTP address and port Meilisearch will use.

### Master key

**Environment variable**: `MEILI_MASTER_KEY`<br />
**CLI option**: `--master-key`<br />
**Default value**: `None`<br />
**Expected value**: a UTF-8 string of at least 16 bytes

Sets the instance's master key, automatically protecting all routes except [`GET /health`](/reference/api/health). This means you will need a valid API key to access all other endpoints.

When `--env` is set to `production`, providing a master key is mandatory. If none is given, or it is under 16 bytes, Meilisearch will throw an error and refuse to launch.

When `--env` is set to `development`, providing a master key is optional. If none is given, all routes will be unprotected and publicly accessible.

If you do not supply a master key in `production` or `development` environments or it is under 16 bytes, Meilisearch will suggest a secure autogenerated master key you can use when restarting your instance.

[Learn more about Meilisearch's use of security keys.](/learn/security/basic_security)

### Disable analytics

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_NO_ANALYTICS`<br />
**CLI option**: `--no-analytics`

Deactivates Meilisearch's built-in telemetry when provided.

Meilisearch automatically collects data from all instances that do not opt out using this flag. All gathered data is used solely for the purpose of improving Meilisearch, and can be [deleted at any time](/learn/resources/telemetry#how-to-delete-all-collected-data).

[Read more about our policy on data collection](/learn/resources/telemetry), or take a look at [the comprehensive list of all data points we collect](/learn/resources/telemetry#exhaustive-list-of-all-collected-data).

### Dumpless upgrade 

**Environment variable**: `MEILI_EXPERIMENTAL_DUMPLESS_UPGRADE`<br />
**CLI option**: `--experimental-dumpless-upgrade`<br />
**Default value**: None<br />
**Expected value**: None

Migrates the database to a new Meilisearch version after you have manually updated the binary.

[Learn more about updating Meilisearch to a new release](/learn/update_and_migration/updating).

#### Create a snapshot before a dumpless upgrade

Take a snapshot of your instance before performing a dumpless upgrade.

Dumpless upgrade are not currently atomic. It is possible some processes fail and Meilisearch still finalizes the upgrade. This may result in a corrupted database and data loss.

### Dump directory

**Environment variable**: `MEILI_DUMP_DIR`<br />
**CLI option**: `--dump-dir`<br />
**Default value**: `dumps/`<br />
**Expected value**: a filepath pointing to a valid directory

Sets the directory where Meilisearch will create dump files.

[Learn more about creating dumps](/reference/api/dump).

### Import dump

**Environment variable**: `MEILI_IMPORT_DUMP`<br />
**CLI option**: `--import-dump`<br />
**Default value**: none<br />
**Expected value**: a filepath pointing to a `.dump` file

Imports the dump file located at the specified path. Path must point to a `.dump` file. If a database already exists, Meilisearch will throw an error and abort launch.

Meilisearch will only launch once the dump data has been fully indexed. The time this takes depends on the size of the dump file.

### Ignore missing dump

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_IGNORE_MISSING_DUMP`<br />
**CLI option**: `--ignore-missing-dump`

Prevents Meilisearch from throwing an error when `--import-dump` does not point to a valid dump file. Instead, Meilisearch will start normally without importing any dump.

This option will trigger an error if `--import-dump` is not defined.

### Ignore dump if DB exists

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_IGNORE_DUMP_IF_DB_EXISTS`<br />
**CLI option**: `--ignore-dump-if-db-exists`

Prevents a Meilisearch instance with an existing database from throwing an error when using `--import-dump`. Instead, the dump will be ignored and Meilisearch will launch using the existing database.

This option will trigger an error if `--import-dump` is not defined.

### Log level

**Environment variable**: `MEILI_LOG_LEVEL`<br />
**CLI option**: `--log-level`<br />
**Default value**: `'INFO'`<br />
**Expected value**: one of `ERROR`, `WARN`, `INFO`, `DEBUG`, `TRACE`, OR `OFF`

Defines how much detail should be present in Meilisearch's logs.

Meilisearch currently supports five log levels, listed in order of increasing verbosity:

- `'ERROR'`: only log unexpected events indicating Meilisearch is not functioning as expected
- `'WARN'`: log all unexpected events, regardless of their severity
- `'INFO'`: log all events. This is the default value of `--log-level`
- `'DEBUG'`: log all events and include detailed information on Meilisearch's internal processes. Useful when diagnosing issues and debugging
- `'TRACE'`: log all events and include even more detailed information on Meilisearch's internal processes. We do not advise using this level as it is extremely verbose. Use `'DEBUG'` before considering `'TRACE'`.
- `'OFF'`: disable logging

### Customize log output 

**Environment variable**: `MEILI_EXPERIMENTAL_LOGS_MODE`<br />
**CLI option**: `--experimental-logs-mode`<br />
**Default value**: `'human'`<br />
**Expected value**: one of `human` or `json`

Defines whether logs should output a human-readable text or JSON data.

### Max indexing memory

**Environment variable**: `MEILI_MAX_INDEXING_MEMORY`<br />
**CLI option**: `--max-indexing-memory`<br />
**Default value**: 2/3 of the available RAM<br />
**Expected value**: an integer (`104857600`) or a human readable size (`'100Mb'`)

Sets the maximum amount of RAM Meilisearch can use when indexing. By default, Meilisearch uses no more than two thirds of available memory.

The value must either be given in bytes or explicitly state a base unit: `107374182400`, `'107.7Gb'`, or `'107374 Mb'`.

It is possible that Meilisearch goes over the exact RAM limit during indexing. In most contexts and machines, this should be a negligible amount with little to no impact on stability and performance.

Setting `--max-indexing-memory` to a value bigger than or equal to your machine's total memory is likely to cause your instance to crash.

### Reduce indexing memory usage 

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_EXPERIMENTAL_REDUCE_INDEXING_MEMORY_USAGE`<br />
**CLI option**: `--experimental-reduce-indexing-memory-usage`<br />
**Default value**: `None`<br />

Enables `MDB_WRITEMAP`, an LMDB option. Activating this option may reduce RAM usage in some UNIX and UNIX-like setups. However, it may also negatively impact write speeds and overall performance.

### Max indexing threads

**Environment variable**: `MEILI_MAX_INDEXING_THREADS`<br />
**CLI option**: `--max-indexing-threads`<br />
**Default value**: half of the available threads<br />
**Expected value**: an integer

Sets the maximum number of threads Meilisearch can use during indexing. By default, the indexer avoids using more than half of a machine's total processing units. This ensures Meilisearch is always ready to perform searches, even while you are updating an index.

If `--max-indexing-threads` is higher than the real number of cores available in the machine, Meilisearch uses the maximum number of available cores.

In single-core machines, Meilisearch has no choice but to use the only core available for indexing. This may lead to a degraded search experience during indexing.

Avoid setting `--max-indexing-threads` to the total of your machine's processor cores. Though doing so might speed up indexing, it is likely to severely impact search experience.

### Payload limit size

**Environment variable**: `MEILI_HTTP_PAYLOAD_SIZE_LIMIT`<br />
**CLI option**: `--http-payload-size-limit`<br />
**Default value**: `104857600` (~100MB)<br />
**Expected value**: an integer

Sets the maximum size of [accepted payloads](/learn/getting_started/documents#dataset-format). Value must be given in bytes or explicitly stating a base unit. e.g., the default value can be written as `107374182400`, `'107.7Gb'`, or `'107374 Mb'`.

### Search queue size 

**Environment variable**: `MEILI_EXPERIMENTAL_SEARCH_QUEUE_SIZE`<br />
**CLI option**: `--experimental-search-queue-size`<br />
**Default value**: `1000`<br />
**Expected value**: an integer

Configure the maximum amount of simultaneous search requests. By default, Meilisearch queues up to 1000 search requests at any given moment. This limit exists to prevent Meilisearch from consuming an unbounded amount of RAM.

### Search query embedding cache 

**Environment variable**: `MEILI_EXPERIMENTAL_EMBEDDING_CACHE_ENTRIES`<br />
**CLI option**: `--experimental-embedding-cache-entries`<br />
**Default value**: `0`<br />
**Expected value**: an integer

Sets the size of the search query embedding cache. By default, Meilisearch generates an embedding for every new search query. When this option is set to an integer bigger than 0, Meilisearch returns a previously generated embedding if it recently performed the same query.

The least recently used entries are evicted first. Embedders with the same configuration share the same cache, even if they were declared in distinct indexes.

### Schedule snapshot creation

**Environment variable**: `MEILI_SCHEDULE_SNAPSHOT`<br />
**CLI option**: `--schedule-snapshot`<br />
**Default value**: disabled if not present, `86400` if present without a value<br />
**Expected value**: `None` or an integer

Activates scheduled snapshots. Snapshots are disabled by default.

It is possible to use `--schedule-snapshot` without a value. If `--schedule-snapshot` is present when launching an instance but has not been assigned a value, Meilisearch takes a new snapshot every 24 hours.

For more control over snapshot scheduling, pass an integer representing the interval in seconds between each snapshot. When `--schedule-snapshot=3600`, Meilisearch takes a new snapshot every hour.

When using the configuration file, it is also possible to explicitly pass a boolean value to `schedule_snapshot`. Meilisearch takes a new snapshot every 24 hours when `schedule_snapshot=true`, and takes no snapshots when `schedule_snapshot=false`.

[Learn more about snapshots](/learn/data_backup/snapshots).

### Snapshot destination

**Environment variable**: `MEILI_SNAPSHOT_DIR`<br />
**CLI option**: `--snapshot-dir`<br />
**Default value**: `snapshots/`<br />
**Expected value**: a filepath pointing to a valid directory

Sets the directory where Meilisearch will store snapshots.

### Uncompressed snapshots 

**Environment variable**: `MEILI_EXPERIMENTAL_NO_SNAPSHOT_COMPACTION`<br />
**CLI option**: `--experimental-no-snapshot-compaction`<br />

Disables snapshot compression. This may significantly speed up snapshot creation at the cost of bigger snapshot files.

### Import snapshot

**Environment variable**: `MEILI_IMPORT_SNAPSHOT`<br />
**CLI option**: `--import-snapshot`<br />
**Default value**: `None`<br />
**Expected value**: a filepath pointing to a snapshot file

Launches Meilisearch after importing a previously-generated snapshot at the given filepath.

This command will throw an error if:

- A database already exists
- No valid snapshot can be found in the specified path

This behavior can be modified with the [`--ignore-snapshot-if-db-exists`](#ignore-snapshot-if-db-exists) and [`--ignore-missing-snapshot`](#ignore-missing-snapshot) options, respectively.

### Ignore missing snapshot

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_IGNORE_MISSING_SNAPSHOT`<br />
**CLI option**: `--ignore-missing-snapshot`

Prevents a Meilisearch instance from throwing an error when [`--import-snapshot`](#import-snapshot) does not point to a valid snapshot file.

This command will throw an error if `--import-snapshot` is not defined.

### Ignore snapshot if DB exists

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_IGNORE_SNAPSHOT_IF_DB_EXISTS`<br />
**CLI option**: `--ignore-snapshot-if-db-exists`

Prevents a Meilisearch instance with an existing database from throwing an error when using `--import-snapshot`. Instead, the snapshot will be ignored and Meilisearch will launch using the existing database.

This command will throw an error if `--import-snapshot` is not defined.

### Task webhook URL

**Environment variable**: `MEILI_TASK_WEBHOOK_URL`<br />
**CLI option**: `--task-webhook-url`<br />
**Default value**: `None`<br />
**Expected value**: a URL string

Notifies the configured URL whenever Meilisearch [finishes processing a task](/learn/async/asynchronous_operations#task-status) or batch of tasks. Meilisearch uses the URL as given, retaining any specified query parameters.

The webhook payload contains the list of finished tasks in [ndjson](https://github.com/ndjson/ndjson-spec). For more information, [consult the dedicated task webhook guide](/learn/async/task_webhook).

The task webhook option requires having access to a command-line interface. If you are using Cloud, use the [`/webhooks` API route](/reference/api/webhooks) instead.

### Task webhook authorization header

**Environment variable**: `MEILI_TASK_WEBHOOK_AUTHORIZATION_HEADER`<br />
**CLI option**: `--task-webhook-authorization-header`<br />
**Default value**: `None`<br />
**Expected value**: an authentication token string

Includes an authentication token in the authorization header when notifying the [webhook URL](#task-webhook-url).

### Maximum number of batched tasks 

**Environment variable**: `MEILI_EXPERIMENTAL_MAX_NUMBER_OF_BATCHED_TASKS`<br />
**CLI option**: `--experimental-max-number-of-batched-tasks`<br />
**Default value**: `None`<br />
**Expected value**: an integer

Limit the number of tasks Meilisearch performs in a single batch. May improve stability in systems handling a large queue of resource-intensive tasks.

### Maximum batch payload size 

**Environment variable**: `MEILI_EXPERIMENTAL_LIMIT_BATCHED_TASKS_TOTAL_SIZE`<br />
**CLI option**: `--experimental-limit-batched-tasks-total-size`<br />
**Default value**: Half of total available memory, up to a maximum of 10 GiB<br />
**Expected value**: an integer

Sets a maximum payload size for batches in bytes. Smaller batches are less efficient, but consume less RAM and reduce immediate latency.

### Replication parameters 

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_EXPERIMENTAL_REPLICATION_PARAMETERS`<br />
**CLI option**: `--experimental-replication-parameters`<br />
**Default value**: `None`<br />

Helps running Meilisearch in cluster environments. It does this by modifying task handling in three ways:

- Task auto-deletion is disabled
- Allows you to manually set task uids by adding a custom `TaskId` header to your API requests
- Allows you to dry register tasks by specifying a `DryRun: true` header in your request

### Disable new indexer 

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_EXPERIMENTAL_NO_EDITION_2024_FOR_SETTINGS`<br />
**CLI option**: `--experimental-no-edition-2024-for-settings`<br />
**Default value**: `None`<br />

Falls back to previous settings indexer.

### Search personalization 

**Environment variable**: `MEILI_EXPERIMENTAL_PERSONALIZATION_API_KEY`<br />
**CLI option**: `--experimental-personalization-api-key`<br />
**Default value**: `None`<br />
**Expected value**: a Cohere API key

Enables search personalization. Must be a valid Cohere API key in string format.

### S3 options

#### Bucket URL

**Environment variable**: `MEILI_S3_BUCKET_URL`<br />
**CLI option**: `--s3-bucket-url`<br />
**Default value**: `None`<br />

The URL for your S3 bucket. The URL must follow the format `https://s3.REGION.amazonaws.com`.

#### Bucket region

**Environment variable**: `MEILI_S3_BUCKET_REGION`<br />
**CLI option**: `--s3-bucket-region`<br />
**Default value**: `None`<br />

The region of your S3 bucket. Must be a valid AWS region, such as `us-east-1`. 

#### Bucket name

**Environment variable**: `MEILI_S3_BUCKET_NAME`<br />
**CLI option**: `--s3-bucket-name`<br />
**Default value**: `None`<br />

The name of your S3 bucket.

#### Snapshot prefix

**Environment variable**: `MEILI_S3_SNAPSHOT_PREFIX`<br />
**CLI option**: `--s3-snapshot-prefix`<br />
**Default value**: `None`<br />

The path leading to the [snapshot directory](#snapshot-destination) in your S3 bucket. Uses normal slashes.

#### Access key

**Environment variable**: `MEILI_S3_ACCESS_KEY`<br />
**CLI option**: `--s3-access-key`<br />
**Default value**: `None`<br />

Your S3 bucket's access key.

#### Secret key

**Environment variable**: `MEILI_S3_SECRET_KEY`<br />
**CLI option**: `--s3-secret-key`<br />
**Default value**: `None`<br />

Your S3 bucket's secret key.

#### Maximum parallel in-flight requests 

**Environment variable**: `MEILI_EXPERIMENTAL_S3_MAX_IN_FLIGHT_PARTS`<br />
**CLI option**: `--experimental-s3-max-in-flight-parts`<br />
**Default value**: `10`<br />

The maximum number of in-flight multipart requests Meilisearch should send to S3 in parallel.

#### Compression level 

**Environment variable**: `MEILI_EXPERIMENTAL_S3_COMPRESSION_LEVEL`<br />
**CLI option**: `--experimental-s3-compression-level`<br />
**Default value**: `0`<br />

The compression level to use for the snapshot tarball. Defaults to 0, no compression.

#### Signature duration 

**Environment variable**: `MEILI_EXPERIMENTAL_S3_SIGNATURE_DURATION_SECONDS`<br />
**CLI option**: `--experimental-s3-signature-duration-seconds`<br />
**Default value**: `28800`<br />

The maximum duration processing a snapshot can take. Defaults to 8 hours.

#### Multipart section size 

**Environment variable**: `MEILI_EXPERIMENTAL_S3_MULTIPART_PART_SIZE`<br />
**CLI option**: `--experimental-s3-multipart-part-size`<br />
**Default value**: `None`<br />

The size of each multipart section. Must be \>10MiB and \<8GiB. Defaults to 375MiB, which enables databases of up to 3.5TiB.

### SSL options

#### SSL authentication path

**Environment variable**: `MEILI_SSL_AUTH_PATH`<br />
**CLI option**: `--ssl-auth-path`<br />
**Default value**: `None`<br />
**Expected value**: a filepath

Enables client authentication in the specified path.

#### SSL certificates path

**Environment variable**: `MEILI_SSL_CERT_PATH`<br />
**CLI option**: `--ssl-cert-path`<br />
**Default value**: `None`<br />
**Expected value**: a filepath pointing to a valid SSL certificate

Sets the server's SSL certificates.

Value must be a path to PEM-formatted certificates. The first certificate should certify the KEYFILE supplied by `--ssl-key-path`. The last certificate should be a root CA.

#### SSL key path

**Environment variable**: `MEILI_SSL_KEY_PATH`<br />
**CLI option**: `--ssl-key-path`<br />
**Default value**: `None`<br />
**Expected value**: a filepath pointing to a valid SSL key file

Sets the server's SSL key files.

Value must be a path to an RSA private key or PKCS8-encoded private key, both in PEM format.

#### SSL OCSP path

**Environment variable**: `MEILI_SSL_OCSP_PATH`<br />
**CLI option**: `--ssl-ocsp-path`<br />
**Default value**: `None`<br />
**Expected value**: a filepath pointing to a valid OCSP certificate

Sets the server's OCSP file. _Optional_

Reads DER-encoded OCSP response from OCSPFILE and staple to certificate.

#### SSL require auth

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_SSL_REQUIRE_AUTH`<br />
**CLI option**: `--ssl-require-auth`<br />
**Default value**: `None`

Makes SSL authentication mandatory.

Sends a fatal alert if the client does not complete client authentication.

#### SSL resumption

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_SSL_RESUMPTION`<br />
**CLI option**: `--ssl-resumption`<br />
**Default value**: `None`

Activates SSL session resumption.

#### SSL tickets

🚩 This option does not take any values. Assigning a value will throw an error. 🚩

**Environment variable**: `MEILI_SSL_TICKETS`<br />
**CLI option**: `--ssl-tickets`<br />
**Default value**: `None`

Activates SSL tickets.

---

## Enterprise and Community editions

## What is the Meilisearch Community Edition?

The Meilisearch Community Edition (CE) is a free version of Meilisearch. It offers all essential Meilisearch features, such as full-text search and AI-powered search, under an MIT license.

## What is the Meilisearch Enterprise Edition?

The Enterprise Edition (EE) is a version of Meilisearch with advanced features. It is available under a BUSL license and cannot be freely used in production. EE is the Meilisearch version that powers Cloud.

The only feature exclusive to the Enterprise Edition is [sharding](/learn/multi_search/implement_sharding).

## When should you use each edition?

In most cases, using Cloud is the recommended way of integrating Meilisearch with your application.

Use the Meilisearch Community Edition when you want to host Meilisearch independently.

Meilisearch makes the Enterprise Edition binaries available for testing EE-only features before committing to a Cloud plan. If you want to self-host the Enterprise Edition in a production environment, [contact the sales team](mailto:sales@meilisearch.com).

---

## Getting started with self-hosted Meilisearch import CodeSamplesGettingStartedAddDocuments from '/snippets/samples/code_samples_getting_started_add_documents.mdx';
import CodeSamplesGettingStartedCheckTaskStatus from '/snippets/samples/code_samples_getting_started_check_task_status.mdx';
import CodeSamplesGettingStartedSearch from '/snippets/samples/code_samples_getting_started_search.mdx';

This quick start walks you through installing Meilisearch, adding documents, and performing your first search.

To follow this tutorial you need:

- A [command line terminal](https://www.learnenough.com/command-line-tutorial#sec-running_a_terminal)
- [cURL](https://curl.se)

Using Cloud? Check out the dedicated guide, [Getting started with Cloud](/learn/getting_started/cloud_quick_start).

## Setup and installation

First, you need to download and install Meilisearch. This command installs the latest Meilisearch version in your local machine:

```bash
# Install Meilisearch curl -L https://install.meilisearch.com | sh
```

The rest of this guide assumes you are using Meilisearch locally, but you may also use Meilisearch over a cloud service such as [Cloud](https://www.meilisearch.com/cloud).

Learn more about other installation options in the [installation guide](/learn/self_hosted/install_meilisearch_locally).

### Running Meilisearch Next, launch Meilisearch by running the following command in your terminal:

```bash
# Launch Meilisearch ./Meilisearch --master-key="aSampleMasterKey"
```

This tutorial uses `aSampleMasterKey` as a master key, but you may change it to any alphanumeric string with 16 or more bytes. In most cases, one character corresponds to one byte.

You should see something like this in response:

```
888b d888 d8b 888 d8b 888
8888b d8888 Y8P 888 Y8P 888
88888b.d88888 888 888
888Y88888P888 .d88b. 888 888 888 .d8888b .d88b. 8888b. 888d888 .d8888b 88888b.
888 Y888P 888 d8P Y8b 888 888 888 88K d8P Y8b "88b 888P" d88P" 888 "88b
888 Y8P 888 88888888 888 888 888 "Y8888b. 88888888 .d888888 888 888 888 888
888 " 888 Y8b. 888 888 888 X88 Y8b. 888 888 888 Y88b. 888 888
888 888 "Y8888 888 888 888 88888P' "Y8888 "Y888888 888 "Y8888P 888 888

Database path: "./data.ms"
Server listening on: "localhost:7700"
```

You now have a Meilisearch instance running in your terminal window. Keep this window open for the rest of this tutorial.

The above command uses the `--master-key` configuration option to secure Meilisearch. Setting a master key is optional but strongly recommended in development environments. Master keys are mandatory in production environments.

To learn more about securing Meilisearch, refer to the [security tutorial](/learn/security/basic_security).

## Add documents

In this quick start, you will search through a collection of movies.

To follow along, first click this link to download the file: <a href="https://www.meilisearch.com/movies.json" download="movies.json">movies.json</a>. Then, move the downloaded file into your working directory.

Meilisearch accepts data in JSON, NDJSON, and CSV formats.

Open a new terminal window and run the following command:

Meilisearch stores data in the form of discrete records, called [documents](/learn/getting_started/documents). Each document is an object composed of multiple fields, which are pairs of one attribute and one value:

```json
{
 "attribute": "value"
}
```

Documents are grouped into collections, called [indexes](/learn/getting_started/indexes).

The previous command added documents from `movies.json` to a new index called `movies`. It also set `id` as the primary key.

Every index must have a [primary key](/learn/getting_started/primary_key#primary-field), an attribute shared across all documents in that index. If you try adding documents to an index and even a single one is missing the primary key, none of the documents will be stored.

If you do not explicitly set the primary key, Meilisearch [infers](/learn/getting_started/primary_key#meilisearch-guesses-your-primary-key) it from your dataset.

After adding documents, you should receive a response like this:

```json
{
 "taskUid": 0,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "documentAdditionOrUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

Use the returned `taskUid` to [check the status](/reference/api/tasks) of your documents:

Most database operations in Meilisearch are [asynchronous](/learn/async/asynchronous_operations). Rather than being processed instantly, **API requests are added to a queue and processed one at a time**.

If the document addition is successful, the response should look like this:

```json
{
 "uid": 0,
 "indexUid": "movies",
 "status": "succeeded",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 19547,
 "indexedDocuments": 19547
 },
 "error": null,
 "duration": "PT0.030750S",
 "enqueuedAt": "2021-12-20T12:39:18.349288Z",
 "startedAt": "2021-12-20T12:39:18.352490Z",
 "finishedAt": "2021-12-20T12:39:18.380038Z"
}
```

If `status` is `enqueued` or `processing`, all you have to do is wait a short time and check again. Proceed to the next step once the task `status` has changed to `succeeded`.

## Search

Now that you have Meilisearch set up, you can start searching!

This tutorial queries Meilisearch with the master key. In production environments, this is a security risk. Prefer using API keys to access Meilisearch's API in any public-facing application.

In the above code sample, the parameter `q` represents the search query. This query instructs Meilisearch to search for `botman` in the documents you added in [the previous step](#add-documents):

```json
{
 "hits": [
 {
 "id": 29751,
 "title": "Batman Unmasked: The Psychology of the Dark Knight",
 "poster": "https://image.tmdb.org/t/p/w1280/jjHu128XLARc2k4cJrblAvZe0HE.jpg",
 "overview": "Delve into the world of Batman and the vigilante justice tha",
 "release_date": "2008-07-15"
 },
 {
 "id": 471474,
 "title": "Batman: Gotham by Gaslight",
 "poster": "https://image.tmdb.org/t/p/w1280/7souLi5zqQCnpZVghaXv0Wowi0y.jpg",
 "overview": "ve Victorian Age Gotham City, Batman begins his war on crime",
 "release_date": "2018-01-12"
 },
 …
 ],
 "estimatedTotalHits": 66,
 "query": "botman",
 "limit": 20,
 "offset": 0,
 "processingTimeMs": 12
}
```

By default, Meilisearch only returns the first 20 results for a search query. You can change this using the [`limit` parameter](/reference/api/search#limit).

## What's next?

You now know how to install Meilisearch, create an index, add documents, check the status of an asynchronous task, and make a search request.

If you'd like to search through the documents you just added using a clean browser interface rather than the terminal, you can do so with [our built-in search preview](/learn/getting_started/search_preview). You can also [learn how to quickly build a front-end interface](/guides/front_end/front_end_integration) of your own.

For a more advanced approach, consult the [API reference](/reference/api/overview).

---

## Install Meilisearch locally

## Cloud

[Cloud](https://www.meilisearch.com/cloud) simplifies installing, maintaining, and updating Meilisearch. [Get started with a 14-day free trial](https://cloud.meilisearch.com/register).

Take a look at the [Cloud tutorial](/learn/getting_started/cloud_quick_start) for more information on setting up and using Meilisearch's cloud service.

## Local installation

Download the **latest stable release** of Meilisearch with **cURL**.

Launch Meilisearch to start the server.

```bash
# Install Meilisearch curl -L https://install.meilisearch.com | sh

# Launch Meilisearch ./Meilisearch ```

Download the **latest stable release** of Meilisearch with **[Homebrew](https://brew.sh/)**, a package manager for MacOS.<br />

Launch Meilisearch to start the server.

```bash
# Update brew and install Meilisearch brew update && brew install Meilisearch # Launch Meilisearch Meilisearch ```

When using **Docker**, you can run [any tag available in our official Docker image](https://hub.docker.com/r/getmeili/meilisearch/tags).<br />

These commands launch the **latest stable release** of Meilisearch.

```bash
# Fetch the latest version of Meilisearch image from DockerHub
docker pull getmeili/meilisearch:v1.16

# Launch Meilisearch in development mode with a master key
docker run -it --rm \
 -p 7700:7700 \
 -e MEILI_ENV='development' \
 -v $(pwd)/meili_data:/meili_data \
 getmeili/meilisearch:v1.16
# Use ${pwd} instead of $(pwd) in PowerShell
```

You can learn more about [using Meilisearch with Docker in our dedicated guide](/guides/docker).

Download the **latest stable release** of Meilisearch with **APT**.<br />

Launch Meilisearch to start the server.

```bash
# Add Meilisearch package
echo "deb [trusted=yes] https://apt.fury.io/meilisearch/ /" | sudo tee /etc/apt/sources.list.d/fury.list

# Update APT and install Meilisearch sudo apt update && sudo apt install Meilisearch # Launch Meilisearch Meilisearch ```

Meilisearch is written in Rust. To compile it, [install the Rust toolchain](https://www.rust-lang.org/tools/install).<br />

Once the Rust toolchain is installed, clone the repository on your local system and change it to your working directory.

```bash
git clone https://github.com/meilisearch/Meilisearch cd Meilisearch ```

Choose the release you want to use. You can find the full list [here](https://github.com/meilisearch/meilisearch/releases).<br />

In the cloned repository, run the following command to access the most recent version of Meilisearch:

```bash
git checkout latest
```

Finally, update the Rust toolchain, compile the project, and execute the binary.

```bash
# Update the Rust toolchain to the latest version
rustup update

# Compile the project
cargo build --release

# Execute the binary
./target/release/Meilisearch ```

To install Meilisearch on Windows, you can:

- Use Docker (see "Docker" tab above)
- Download the latest binary (see "Direct download" tab above)
- Use the installation script (see "cURL" tab above) if you have installed [Cygwin](https://www.cygwin.com/), [WSL](https://learn.microsoft.com/en-us/windows/wsl/), or equivalent
- Compile from source (see "Source" tab above)

To learn more about the Windows command prompt, follow this [introductory guide](https://www.makeuseof.com/tag/a-beginners-guide-to-the-windows-command-line/).

If none of the other installation options work for you, you can always download the Meilisearch binary directly on GitHub.<br />

Go to the [latest Meilisearch release](https://github.com/meilisearch/meilisearch/releases/latest), scroll down to "Assets", and select the binary corresponding to your operating system.

```bash
# Rename binary to meilisearch. Replace {meilisearch_os} with the name of the downloaded binary
mv {meilisearch_os} Meilisearch # Give the binary execute permission
chmod +x Meilisearch # Launch Meilisearch ./Meilisearch ```

## Installing older versions of Meilisearch We discourage the use of older Meilisearch versions. Before installing an older version, please [contact support](https://discord.meilisearch.com) to check if the latest version might work as well.

Download the binary of a specific version under "Assets" on our [GitHub changelog](https://github.com/meilisearch/meilisearch/releases).

```bash
# Replace {meilisearch_version} and {meilisearch_os} with the specific version and OS you want to download
# e.g., if you want to download v1.0 on macOS,
# replace {meilisearch_version} and {meilisearch_os} with v1.0 and meilisearch-macos-amd64 respectively
curl -OL https://github.com/meilisearch/meilisearch/releases/download/{meilisearch_version}/{meilisearch_os}

# Rename binary to meilisearch. Replace {meilisearch_os} with the name of the downloaded binary
mv {meilisearch_os} Meilisearch # Give the binary execute permission
chmod +x Meilisearch # Launch Meilisearch ./Meilisearch ```

When using **Docker**, you can run [any tag available in our official Docker image](https://hub.docker.com/r/getmeili/meilisearch/tags).<br />

```bash
# Fetch specific version of Meilisearch image from DockerHub. Replace vX.Y.Z with the version you want to use
docker pull getmeili/meilisearch:vX.Y.Z

# Launch Meilisearch in development mode with a master key
docker run -it --rm \
 -p 7700:7700 \
 -e MEILI_ENV='development' \
 -v $(pwd)/meili_data:/meili_data \
 getmeili/meilisearch:vX.Y.Z
# Use ${pwd} instead of $(pwd) in PowerShell
```

Learn more about [using Meilisearch with Docker in our dedicated guide](/guides/docker).

Meilisearch is written in Rust. To compile it, [install the Rust toolchain](https://www.rust-lang.org/tools/install).<br />

Once the Rust toolchain is installed, clone the repository on your local system and change it to your working directory.

```bash
git clone https://github.com/meilisearch/Meilisearch cd Meilisearch ```

Choose the release you want to use. You can find the full list [here](https://github.com/meilisearch/meilisearch/releases).<br />

In the cloned repository, run the following command to access a specific version of Meilisearch:

```bash
# Replace vX.Y.Z with the specific version you want to use
git checkout vX.Y.Z
```

Finally, update the Rust toolchain, compile the project, and execute the binary.

```bash
# Update the Rust toolchain to the latest version
rustup update

# Compile the project
cargo build --release

# Execute the binary
./target/release/Meilisearch ```

Download the binary of a specific version under "Assets" on our [GitHub changelog](https://github.com/meilisearch/meilisearch/releases).

```bash
# Rename binary to meilisearch. Replace {meilisearch_os} with the name of the downloaded binary
mv {meilisearch_os} Meilisearch # Give the binary execute permission
chmod +x Meilisearch # Launch Meilisearch ./Meilisearch ```

---

## Supported operating systems

Meilisearch officially supports Windows, MacOS, and many Linux distributions. Consult the [installation guide](/learn/self_hosted/install_meilisearch_locally) for more instructions.

Meilisearch binaries might still run in supported environments without official support.

Use [Cloud](https://www.meilisearch.com/cloud) to integrate Meilisearch with applications hosted in unsupported operating systems.

## Linux

The Meilisearch binary works on all Linux distributions with `amd64/x86_64` or `aarch64/arm64` architecture using glibc 2.35 and later. You can check your glibc version using:

```
ldd --version
```

## macOS

The Meilisearch binary works with macOS 14 Sonoma and later with `amd64` or `arm64` architecture. Older macOS versions might be compatible with Meilisearch but are not officially supported.

## Windows

The Meilisearch binary works on Windows Server 2022 and later.

It is likely the Meilisearch binary also works with Windows OS 10 and later. However, due to the differences between Windows OS and Windows Server, Meilisearch does not officially support Windows OS.

## Troubleshooting

If the provided [binaries](https://github.com/meilisearch/meilisearch/releases) do not work on your operating system, try building Meilisearch [from source](/learn/self_hosted/install_meilisearch_locally#local-installation). If compilation fails, Meilisearch is not compatible with your machine.

---

## Cloud teams

Cloud teams are groups of users who all have access a to specific set of projects. This feature is designed to help collaboration between project stakeholders with different skillsets and responsibilities.

When you open a new account, Cloud automatically creates a default team. A team may have any number of team members.

## Team roles and permissions

There are two types of team members in Cloud teams: owners and regular team members.

Team owners have full control over a project's administrative details. Only team owners may change a project's billing plan or update its billing information. Additionally, only team owners may rename a team, add and remove members from a team, or transfer team ownership.

A team may only have one owner.

## Multiple teams in the same account

If you are responsible for different applications belonging to multiple organizations, it might be useful to create separate teams. There are no limits for the amount of teams a single user may create.

It is not possible to delete a team once you have created it. However, Cloud billing is based on projects and there are no costs associated with creating multiple teams.

---

## Migrating from Algolia to Meilisearch This page aims to help current users of Algolia make the transition to Meilisearch.

For a high-level comparison of the two search companies and their products, see [our analysis of the search market](/learn/resources/comparison_to_alternatives#meilisearch-vs-algolia).

## Overview

This guide will take you step-by-step through the creation of a [Node.js](https://nodejs.org/en/) script to upload Algolia index data to Meilisearch. [You can also skip directly to the finished script](#finished-script).

The migration process consists of three steps:

1. [Export your data stored in Algolia](#export-your-algolia-data)
2. [Import your data into Meilisearch](#import-your-data-into-meilisearch)
3. [Configure your Meilisearch index settings (optional)](#configure-your-index-settings)

To help with the transition, we have also included a comparison of Meilisearch and Algolia's [API methods](#api-methods) and [front-end components](#front-end-components).

Before continuing, make sure you have both Meilisearch and Node.js installed and have access to a command-line terminal. If you're unsure how to install Meilisearch, see our [quick start](/learn/self_hosted/getting_started_with_self_hosted_meilisearch).

This guide was tested with the following package versions:

- [`node.js`](https://nodejs.org/en/): `16.16`
- [`algoliasearch`](https://www.npmjs.com/package/algoliasearch): `4.13`
- [`meilisearch-js`](https://www.npmjs.com/package/meilisearch): `0.27.0`
- [`meilisearch`](https://github.com/meilisearch/meilisearch): `0.28`

## Export your Algolia data

### Initialize project

Start by creating a directory `algolia-meilisearch-migration` and generating a `package.json` file with `npm`:

```bash
mkdir algolia-meilisearch-migration
cd algolia-meilisearch-migration
npm init -y
```

This will set up the environment we need to install dependencies.

Next, create a `script.js` file:

```bash
touch script.js
```

This file will contain our migration script.

### Install dependencies

To get started, you'll need two different packages. The first is `algoliasearch`, the JavaScript client for the Algolia API, and the second is `meilisearch`, the JavaScript client for the Meilisearch API.

```bash
npm install -s algoliasearch@4.13 meilisearch@0.25.1
```

### Create Algolia client

You'll need your **Application ID** and **Admin API Key** to start the Algolia client. Both can be found in your [Algolia account](https://www.algolia.com/account/api-keys).

Paste the below code in `script.js`:

```js
const algoliaSearch = require("algoliasearch");

const algoliaClient = algoliaSearch(
 "APPLICATION_ID",
 "ADMIN_API_KEY"
);
const algoliaIndex = algoliaClient.initIndex("INDEX_NAME");
```

Replace `APPLICATION_ID` and `ADMIN_API_KEY` with your Algolia application ID and admin API key respectively.

Replace `INDEX_NAME` with the name of the Algolia index you would like to migrate to Meilisearch.

### Fetch data from Algolia

To fetch all Algolia index data at once, use Algolia's [`browseObjects`](https://www.algolia.com/doc/api-reference/api-methods/browse/) method.

```js
let records = [];
await algoliaIndex.browseObjects({
 batch: (hits) => {
 records = records.concat(hits);
 }
 });
```

The `batch` callback method is invoked on each batch of hits and the content is concatenated in the `records` array. We will use `records` again later in the upload process.

## Import your data into Meilisearch ### Create Meilisearch client

Create a Meilisearch client by passing the host URL and API key of your Meilisearch instance. The easiest option is to use the automatically generated [admin API key](/learn/security/basic_security).

```js
const { Meilisearch } = require("meilisearch");

const meiliClient = new MeiliSearch({
 host: "MEILI_HOST",
 apiKey: "MEILI_API_KEY",
});
const meiliIndex = meiliClient.index("MEILI_INDEX_NAME");
```

Replace `MEILI_HOST`,`MEILI_API_KEY`, and `MEILI_INDEX_NAME` with your Meilisearch host URL, Meilisearch API key, and the index name where you would like to add documents. Meilisearch will create the index if it doesn't already exist.

### Upload data to Meilisearch Next, use the Meilisearch JavaScript method [`addDocumentsInBatches`](https://github.com/meilisearch/meilisearch-js#documents-) to upload all your records in batches of 100,000.

```js
const BATCH_SIZE = 100000;
await meiliIndex.addDocumentsInBatches(records, BATCH_SIZE);
```

That's all! When you're ready to run the script, enter the below command:

```bash
node script.js
```

### Finished script

```js
const algoliaSearch = require("algoliasearch");
const { Meilisearch } = require("meilisearch");

const BATCH_SIZE = 1000;

(async () => {
 const algoliaClient = algoliaSearch("APPLICATION_ID", "ADMIN_API_KEY");
 const algoliaIndex = algoliaClient.initIndex("INDEX_NAME");

 let records = [];
 await algoliaIndex.browseObjects({
 batch: (hits) => {
 records = records.concat(hits);
 }
 });

 const meiliClient = new MeiliSearch({
 host: "MEILI_HOST",
 apiKey: "MEILI_API_KEY",
 });
 const meiliIndex = meiliClient.index("MEILI_INDEX_NAME");

 await meiliIndex.addDocumentsInBatches(records, BATCH_SIZE);
})();
```

## Configure your index settings

Meilisearch's default settings are designed to deliver a fast and relevant search experience that works for most use-cases.

To customize your index settings, we recommend following [this guide](/learn/getting_started/indexes#index-settings). To learn more about the differences between settings in Algolia and Meilisearch, read on.

### Index settings vs. search parameters

One of the key usage differences between Algolia and Meilisearch is how they approach index settings and search parameters.

**In Algolia,** [API parameters](https://www.algolia.com/doc/api-reference/api-parameters/) is a flexible category that includes both index settings and search parameters. Many API parameters can be used both at indexing time—to set default behavior—or at search time—to override that behavior.

**In Meilisearch,** [index settings](/reference/api/settings) and [search parameters](/reference/api/search#search-parameters) are two distinct categories. Settings affect all searches on an index, while parameters affect the results of a single search.

Some Meilisearch parameters require index settings to be configured beforehand. e.g., you must first configure the index setting `sortableAttributes` to use the search parameter `sort`. However, unlike in Algolia, an index setting can never be used as a parameter and vice versa.

### Settings and parameters comparison

The below table compares Algolia's **API parameters** with the equivalent Meilisearch **setting** or **search parameter**. | Algolia | Meilisearch | | :--- | :--- | | `query` | `q` | | `attributesToRetrieve` | `attributesToRetrieve` | | `filters` | `filter` | | `facets` | `facetDistribution` | | `attributesToHighlight` | `attributesToHighlight` | | `offset` | `offset` | | `length` | `limit` | | `typoTolerance` | `typoTolerance` | | `snippetEllipsisText` | `cropMarker` | | `searchableAttributes` | `searchableAttributes` | | `attributesForFaceting` | `filterableAttributes` | | `unretrievableAttributes` | No direct equivalent; achieved by removing attributes from `displayedAttributes` | | `attributesToRetrieve` | `displayedAttributes` | | `attributeForDistinct` | `distinctAttribute` | | `ranking` | `rankingRules` | | `customRanking` | Integrated within `rankingRules` | | `removeStopWords` | `stopWords` | | `synonyms` | `synonyms` | | Sorting(using replicas) | `sortableAttributes` (no replicas required) | | `removeWordsIfNoResults` | Automatically supported, but not customizable | | `disableTypoToleranceOnAttributes` | `typoTolerance.disableOnAttributes` | | `separatorsToIndex` | Not Supported | | `disablePrefixOnAttributes` | Not Supported | | `relevancyStrictness` | Not Supported | | `maxValuesPerFacet` | `maxValuesPerFacet` | | `sortFacetValuesBy` | `sortFacetValuesBy` | | `restrictHighlightAndSnippetArrays` | Not Supported | ## API methods

This section compares Algolia and Meilisearch's respective API methods, using JavaScript for reference. | Method | Algolia | Meilisearch | | :--- | :--- | :--- | | Index Instantiation | `client.initIndex()`<br />Here, client is an Algolia instance. | `client.index()`<br />Here, client is a Meilisearch instance. | | Create Index | Algolia automatically creates an index the first time you add a record or settings. | The same applies to Meilisearch, but users can also create an index explicitly: `client.createIndex(string indexName)` | | Get All Indexes | `client.listIndices()` | `client.getIndexes()` | | Get Single Index | No method available | `client.getIndex(string indexName)` | | Delete Index | `index.delete()` | `client.deleteIndex(string indexName)` | | Get Index Settings | `index.getSettings()` | `index().getSettings()` | | Update Index Settings | `index.setSettings(object settings)` | `index().updateSettings(object settings)` | | Search Method | `index.search(string query, { searchParameters, requestOptions })` | `index.search(string query, object searchParameters)` | | Add Object | `index.saveObjects(array objects)` | `index.addDocuments(array objects)` | | Partial Update Object | `index.partialUpdateObjects(array objects)` | `index.updateDocuments(array objects)` | | Delete All Objects | `index.deleteObjects(array objectIDs)` | `index.deleteAllDocuments()` | | Delete One Object | `index.deleteObject(string objectID)` | `index.deleteDocument(string id)` | | Get All Objects | `index.getObjects(array objectIDs)` | `index.getDocuments(object params)` | | Get Single Object | `index.getObject(str objectID)` | `index.getDocument(string id)` | | Get API Keys | `client.listApiKeys()` | `client.getKeys()` | | Get API Key Info | `client.getApiKey(string apiKey)` | `client.getKey(string apiKey)` | | Create API Key | `client.addApiKey(array acl)` | `client.createKey(object configuration)` | | Update API Key | `client.updateApiKey(string apiKey, object configuration)` | `client.updateKey(string apiKey, object configuration)` | | Delete API Key | `client.deleteApiKey(string apiKey)` | `client.deleteKey(string apiKey)` | ## Front-end components

[InstantSearch](https://github.com/algolia/instantsearch.js) is a collection of open-source tools maintained by Algolia and used to generate front-end search UI components. To use InstantSearch with Meilisearch, you must use [Instant Meilisearch](https://github.com/meilisearch/meilisearch-js-plugins/tree/main/packages/instant-meilisearch).

Instant Meilisearch is a plugin connecting your Meilisearch instance with InstantSearch, giving you access to many of the same front-end components as Algolia users. You can find an up-to-date list of [the components supported by Instant Meilisearch](https://github.com/meilisearch/meilisearch-js-plugins/tree/main/packages/instant-meilisearch#-api-resources) in the GitHub project's README.

---

## Migrating to Cloud — Meilisearch Documentation

Cloud is the recommended way of using Meilisearch. This guide walks you through migrating Meilisearch from a self-hosted installation to Cloud.

## Requirements

To follow this guide you need:

- A running Meilisearch instance
- A command-line terminal
- A Cloud account

## Export a dump from your self-hosted installation

To migrate Meilisearch, you must first [export a dump](/learn/data_backup/dumps). A dump is a compressed file containing all your indexes, documents, and settings.

To export a dump, make sure your self-hosted Meilisearch instance is running. Then, open your terminal and run the following command, replacing `MEILISEARCH_URL` with your instance's address:

```sh
curl -X POST 'MEILISEARCH_URL:7700/dumps'
```

Meilisearch will return a summarized task object and begin creating the dump. [Use the returned object's `taskUid` to monitor its progress.](/learn/async/asynchronous_operations)

Once the task has been completed, you can find the dump in your project's dump directory. By default, this is `/dumps`.

Instance configuration options and experimental features that can only be activated at launch are not included in dumps.

Once you have successfully migrated your data to Cloud, use the project overview interface to reactivate available options. Not all instance options are supported in the Cloud.

## Create a Cloud project and import dump

Navigate to Cloud in your browser and log in. If you don't have a Cloud account yet, [create one for free](https://cloud.meilisearch.com/register?utm_campaign=oss&utm_source=docs&utm_medium=migration-guide).

You can only import dumps into new Cloud projects. If this is your first time using Cloud, create a new project by clicking on the "Create a project" button. Otherwise, click on the "New project" button:

 <img src="/assets/images/cloud-migration/1-new-project.png" alt="The Cloud menu, featuring the 'New Project' button" />

Fill in your project name, choose a server location, and select your plan. Then, click on the "Import .dump" button and select the dump file you generated in the previous step:

 <img src="/assets/images/cloud-migration/2-import-dump.png" alt="A modal window with three mandatory fields: 'Project name', 'Select a region', and 'Select a plan'. Further down, an optional field: 'Import .dump'" />

Meilisearch will start creating a new project and importing your data. This might take a few moments depending on the size of your dataset. Monitor the project creation status in the project overview page.

Cloud automatically generates a new master key during project creation. If you are using [security keys](/learn/security/basic_security), update your application so it uses the newly created Cloud API keys.

## Search preview

Once your project is ready, click on it to enter the project overview. From there, click on "Search preview" in the top bar menu. This will bring you to the search preview interface. Run a few test searches to ensure all data was migrated successfully.

Congratulations, you have now migrated to Cloud, the recommended way to use Meilisearch. If you encountered any problems during this process, reach out to our support team on [Discord](https://discord.meilisearch.com).

---

## Accessing previous docs versions

This documentation website only covers the latest stable release of Meilisearch. However, it is possible to view the documentation of previous Meilisearch versions stored in [our GitHub repository](https://github.com/meilisearch/documentation).

This guide shows you how to clone Meilisearch's documentation repository, fetch the content for a specific version, and read it on your local machine.

While this guide's goal is to help users of old versions accomplish their bare minimum needs, it is not intended as a long-term solution or to encourage users to continue using outdated versions of Meilisearch. In almost every case, **it is better to upgrade to the latest Meilisearch version**.

Depending on the version in question, the process of accessing old documentation may be difficult or error-prone. You have been warned!

## Prerequisites

To follow this guide, you should have some familiarity with the command line. Before beginning, make sure the following tools are installed on your machine:

- [Git](https://git-scm.com/)
- [Node v14](https://nodejs.org/en/)
- [Yarn](https://classic.yarnpkg.com/en/)
- [Python 3](https://www.python.org)

## Clone the repository

To access previous versions of the Meilisearch documentation, the first step is downloading the documentation repository into your local machine. In Git, this is referred to as cloning.

Open your console and run the following command. It will create a `documentation` directory in your current location containing the Meilisearch documentation site project files:

```sh
git clone https://github.com/meilisearch/documentation.git
```

Alternatively, you may [clone the repository using an SSH URL](https://docs.github.com/en/get-started/getting-started-with-git/about-remote-repositories#cloning-with-ssh-urls).

## Select a Meilisearch version

The documentation repository contains tags for versions from `v0.8` up to the latest release. Use these tags together with `git checkout` to access a specific version.

e.g., the following command retrieves the Meilisearch v0.20 documentation:

```sh
git checkout v0.20
```

Visit the repository on GitHub to [view all documentation tags](https://github.com/meilisearch/documentation/tags).

## Access the documentation

There are different ways of accessing the documentation of previous Meilisearch releases depending on the version you checked out.

The site search bar is not functional in local copies of the documentation website.

### >= v1.2: read `.mdx` files

Starting with v1.2, Meilisearch's documentation content and build code live in separate repositories. Because of this, it is not possible to run a local copy of the documentation website.

To access the Meilisearch documentation for versions 1.2 and later, read the `.mdx` files directly, either locally with the help of a modern text editor or remotely using GitHub's interface.

### v0.17-v1.1: run a local Vuepress server

#### Install dependencies

This version of the Meilisearch documentation manages its dependencies with Yarn. Run the following command to install all required packages:

```sh
yarn install
```

#### Start the local server

After installing dependencies, use Yarn to start the server:

```sh
yarn dev
```

Yarn will build the website from the markdown source files. Once the server is online, use your browser to navigate to `http://localhost:8080`.

SDK code samples are not available in local copies of the documentation for Meilisearch v0.17 - v1.1.

### v0.11-v0.16: run a simple Python server

Accessing Meilisearch documentation from v0.11 to v0.16 requires launching an HTTP server on your local machine. Run the following command on your console:

```sh
python3 -m http.server 8080
```

Once the server is online, use your browser to navigate to `http://localhost:8080`.

The above example uses Python to launch a local server, but alternatives such as `npx serve` work equally well.

### v0.8 to v0.10: read markdown source files

The build workflow on early versions of the documentation website involves multiple deprecated tools and libraries. Browse the source markdown files, either locally with the help of a modern text editor or remotely using GitHub's interface.

---

## Update to the latest Meilisearch version

import { NoticeTag } from '/snippets/notice_tag.mdx';

import CodeSamplesUpdatingGuideCheckVersionNewAuthorizationHeader from '/snippets/samples/code_samples_updating_guide_check_version_new_authorization_header.mdx';
import CodeSamplesUpdatingGuideCheckVersionOldAuthorizationHeader from '/snippets/samples/code_samples_updating_guide_check_version_old_authorization_header.mdx';
import CodeSamplesUpdatingGuideCreateDump from '/snippets/samples/code_samples_updating_guide_create_dump.mdx';
import CodeSamplesUpdatingGuideGetDisplayedAttributesOldAuthorizationHeader from '/snippets/samples/code_samples_updating_guide_get_displayed_attributes_old_authorization_header.mdx';
import CodeSamplesUpdatingGuideResetDisplayedAttributesOldAuthorizationHeader from '/snippets/samples/code_samples_updating_guide_reset_displayed_attributes_old_authorization_header.mdx';

Currently, Meilisearch databases are only compatible with the version of Meilisearch used to create them. The following guide will walk you through using a [dump](/learn/data_backup/dumps) to migrate an existing database from an older version of Meilisearch to the most recent one.

If you're updating your Meilisearch instance on cloud platforms like DigitalOcean or AWS, ensure that you can connect to your cloud instance via SSH. Depending on the user you are connecting with (root, admin, etc.), you may need to prefix some commands with `sudo`.

If migrating to the latest version of Meilisearch will cause you to skip multiple versions, this may require changes to your codebase. [Refer to our version-specific update warnings for more details](#version-specific-warnings).

If you are running Meilisearch as a `systemctl` service using v0.22 or above, try our [migration script](https://github.com/meilisearch/meilisearch-migration).

## Updating Cloud

Log into your Cloud account and navigate to the project you want to update.

Click on the project you want to update. Look for the "General settings" section at the top of the page.

Whenever a new version of Meilisearch is available, you will see an update button next to the "Meilisearch version" field.

 <img src="/assets/images/updating/update-button.png" alt="Button to update Meilisearch version to 1.0.2" />

To update to the latest Meilisearch release, click the "Update to v.X.Y.Z" button.

This will open a pop-up with more information about the update process. Read it, then click on "Update". The "Status" of your project will change from "running" to "updating".

 <img src="/assets/images/updating/update-in-progress.png" alt="Project update in progress" />

Once the project has been successfully updated, you will receive an email confirming the update and "Status" will change back to "running".

## Updating a self-hosted Meilisearch instance

You may update a self-hosted instance in one of two ways: with or without a dump.

This guide only works for v0.15 and above. If you are using an older Meilisearch release, please [contact support](https://discord.meilisearch.com) for more information.

### Dumpless upgrade 

Dumpless upgrades are available when upgrading from Meilisearch >=v1.12 to Meilisearch >=v1.13

#### Step 1: Make a backup

Dumpless upgrades are an experimental feature. Because of that, it may in rare occasions partially fail and result in a corrupted database. To prevent data loss, create a snapshot of your instance:

```sh
curl \
 -X POST 'MEILISEARCH_URL/snapshots'
```

Meilisearch will respond with a partial task object. Use its `taskUid` to monitor the snapshot creation status. Once the task is completed, proceed to the next step.

### Step 2: Stop the Meilisearch instance

Next, stop your Meilisearch instance.

If you're running Meilisearch locally, stop the program by pressing `Ctrl + c`.

If you're running Meilisearch as a `systemctl` service, connect via SSH to your cloud instance and execute the following command to stop Meilisearch:

```bash
systemctl stop Meilisearch ```

You may need to prefix the above command with `sudo` if you are not connected as root.

#### Step 3: Install the new Meilisearch binary

Install the latest version of Meilisearch using:

[cURL example omitted]

```sh
# replace MEILISEARCH_VERSION with the version of your choice. Use the format: `vX.X.X`
curl "https://github.com/meilisearch/meilisearch/releases/download/MEILISEARCH_VERSION/meilisearch-linux-amd64" --output Meilisearch --location --show-error
```

Give execute permission to the Meilisearch binary:

```
chmod +x Meilisearch ```

For **cloud platforms**, move the new Meilisearch binary to the `/usr/bin` directory:

```
mv Meilisearch /usr/bin/Meilisearch ```

#### Step 4: Relaunch Meilisearch Execute the command below to import the dump at launch:

```bash
./Meilisearch --experimental-dumpless-upgrade 
```

```sh
Meilisearch --experimental-dumpless-upgrade 
```

Meilisearch should launch normally and immediately create a new `UpgradeDatabase` task. This task is processed immediately and cannot be canceled. You may follow its progress by using the `GET /tasks?types=UpgradeDatabase` endpoint to obtain its `taskUid`, then querying `GET /tasks/TASK_UID`.

While the task is processing, you may continue making search queries. You may also enqueue new tasks. Meilisearch will only process new tasks once `UpgradeDatabase` is completed.

#### Rolling back an update

If the upgrade is taking too long, or if after the upgrade is completed its task status is set to `failed`, you can cancel the upgrade task.

Cancelling the update task automatically rolls back your database to its state before the upgrade began.

After launching Meilisearch with `--experimental-dumpless-upgrade` flag:

1. Cancel the `upgradeDatabase` task
2. If you cancelled the update before it failed, skip to the next step. If the update failed, relaunch Meilisearch using the binary of the version you were upgrading to
3. Wait for Meilisearch to process your cancellation request
4. Replace the new binary with the binary of the previous version
5. Relaunch Meilisearch If you are upgrading Meilisearch to \<= v1.14, you must instead [restart your instance from the snapshot](/learn/data_backup/snapshots#starting-from-a-snapshot) you generated during step 1. You may then retry the upgrade, or upgrade using a dump. You are also welcome to open an issue on the [Meilisearch repository](https://github.com/meilisearch/meilisearch).

### Using a dump

#### Step 1: Export data

##### Verify your database version

First, verify the version of Meilisearch that's compatible with your database using the get version endpoint:

The response should look something like this:

```json
{
 "commitSha": "stringOfLettersAndNumbers",
 "commitDate": "YYYY-MM-DDTimestamp",
 "pkgVersion": "x.y.z"
}
```

If you get the `missing_authorization_header` error, you might be using **v0.24 or below**. For each command, replace the `Authorization: Bearer` header with the `X-Meili-API-Key: API_KEY` header:

If your [`pkgVersion`](/reference/api/version#version-object) is 0.21 or above, you can jump to [creating the dump](#create-the-dump). If not, proceed to the next step.

##### Set all fields as displayed attributes

If your dump was created in Meilisearch v0.21 or above, [skip this step](#create-the-dump).

When creating dumps using Meilisearch versions below v0.21, all fields must be [displayed](/learn/relevancy/displayed_searchable_attributes#displayed-fields) to be saved in the dump.

Start by verifying that all attributes are included in the displayed attributes list:

If the response for all indexes is `{'displayedAttributes': '["*"]'}`, you can move on to the [next step](#create-the-dump).

If the response is anything else, save the current list of displayed attributes in a text file and then reset the displayed attributes list to its default value `(["*"])`:

This command returns an `updateId`. Use the get update endpoint to track the status of the operation:

```sh
 # replace {indexUid} with the uid of your index and {updateId} with the updateId returned by the previous request
 curl \
 -X GET 'http://<your-domain-name>/indexes/{indexUid}/updates/{updateId}'
 -H 'X-Meili-API-Key: API_KEY'
```

Once the status is `processed`, you're good to go. Repeat this process for all indexes, then move on to creating your dump.

##### Create the dump

Before creating your dump, make sure that your [dump directory](/learn/self_hosted/configure_meilisearch_at_launch#dump-directory) is somewhere accessible. By default, dumps are created in a folder called `dumps` at the root of your Meilisearch directory.

**Cloud platforms** like DigitalOcean and AWS are configured to store dumps in the `/var/opt/meilisearch/dumps` directory.

If you're unsure where your Meilisearch directory is located, try this:

```bash
which Meilisearch ```

It should return something like this:

```bash
/absolute/path/to/your/meilisearch/directory
```

```bash
where Meilisearch ```

It should return something like this:

```bash
/absolute/path/to/your/meilisearch/directory
```

```bash
(Get-Command meilisearch).Path
```

It should return something like this:

```bash
/absolute/path/to/your/meilisearch/directory
```

Due to an error allowing malformed `_geo` fields in Meilisearch **v0.27, v0.28, and v0.29**, you might not be able to import your dump. Please ensure the `_geo` field follows the [correct format](/learn/filtering_and_sorting/geosearch#preparing-documents-for-location-based-search) before creating your dump.

You can then create a dump of your database:

The server should return a response that looks like this:

```json
{
 "taskUid": 1,
 "indexUid": null,
 "status": "enqueued",
 "type": "dumpCreation",
 "enqueuedAt": "2022-06-21T16:10:29.217688Z"
}
```

Use the `taskUid` to [track the status](/reference/api/tasks#get-one-task) of your dump. Keep in mind that the process can take some time to complete.

For v0.27 and below, the response to your request returns a dump `uid`. Use it with the `/dumps/:dump_uid/status` route to track the request status:

```sh
 curl \
 -X GET 'http://<your-domain-name>/dumps/:dump_uid/status'
 -H 'Authorization: Bearer API_KEY'
 # -H 'X-Meili-API-Key: API_KEY' for v0.24 or below
```

Once the `dumpCreation` task shows `"status": "succeeded"`, you're ready to move on.

#### Step 2: Prepare for migration

##### Stop the Meilisearch instance

Stop your Meilisearch instance.

If you're running Meilisearch locally, you can stop the program with `Ctrl + c`.

If you're running Meilisearch as a `systemctl` service, connect via SSH to your cloud instance and execute the following command to stop Meilisearch:

```bash
systemctl stop Meilisearch ```

You may need to prefix the above command with `sudo` if you are not connected as root.

##### Create a backup

Instead of deleting `data.ms`, we suggest creating a backup in case something goes wrong. `data.ms` should be at the root of the Meilisearch binary unless you chose [another location](/learn/self_hosted/configure_meilisearch_at_launch#database-path).

On **cloud platforms**, you will find the `data.ms` folder at `/var/lib/meilisearch/data.ms`.

Move the binary of the current Meilisearch installation and database to the `/tmp` folder:

```
mv /path/to/your/meilisearch/directory/meilisearch/data.ms /tmp/
mv /path/to/your/meilisearch/directory/Meilisearch /tmp/
```

```
mv /usr/bin/Meilisearch /tmp/
mv /var/lib/meilisearch/data.ms /tmp/
```

##### Install the desired version of Meilisearch Install the latest version of Meilisearch using:

[cURL example omitted]

```sh
# replace {meilisearch_version} with the version of your choice. Use the format: `vX.X.X`
curl "https://github.com/meilisearch/meilisearch/releases/download/{meilisearch_version}/meilisearch-linux-amd64" --output Meilisearch --location --show-error
```

Give execute permission to the Meilisearch binary:

```
chmod +x Meilisearch ```

For **cloud platforms**, move the new Meilisearch binary to the `/usr/bin` directory:

```
mv Meilisearch /usr/bin/Meilisearch ```

#### Step 3: Import data

##### Launch Meilisearch and import the dump

Execute the command below to import the dump at launch:

```bash
# replace {dump_uid.dump} with the name of your dump file
./Meilisearch --import-dump dumps/{dump_uid.dump} --master-key="MASTER_KEY"
# Or, if you chose another location for data files and dumps before the update, also add the same parameters
./Meilisearch --import-dump dumps/{dump_uid.dump} --master-key="MASTER_KEY" --db-path PATH_TO_DB_DIR/data.ms --dump-dir PATH_TO_DUMP_DIR/dumps
```

```sh
# replace {dump_uid.dump} with the name of your dump file
Meilisearch --db-path /var/lib/meilisearch/data.ms --import-dump "/var/opt/meilisearch/dumps/{dump_uid.dump}"
```

Importing a dump requires indexing all the documents it contains. Depending on the size of your dataset, this process can take a long time and cause a spike in memory usage.

##### Restart Meilisearch as a service

If you're running a **cloud instance**, press `Ctrl`+`C` to stop Meilisearch once your dump has been correctly imported. Next, execute the following command to run the script to configure Meilisearch and restart it as a service:

```
meilisearch-setup
```

If required, set `displayedAttributes` back to its previous value using the [update displayed attributes endpoint](/reference/api/settings#update-displayed-attributes).

### Conclusion

Now that your updated Meilisearch instance is up and running, verify that the dump import was successful and no data was lost.

If everything looks good, then congratulations! You successfully migrated your database to the latest version of Meilisearch. Be sure to check out the [changelogs](https://github.com/meilisearch/MeiliSearch/releases).

If something went wrong, you can always roll back to the previous version. Feel free to [reach out for help](https://discord.meilisearch.com) if the problem continues. If you successfully migrated your database but are having problems with your codebase, be sure to check out our [version-specific warnings](#version-specific-warnings).

#### Delete backup files or rollback (_optional_)

Delete the Meilisearch binary and `data.ms` folder created by the previous steps. Next, move the backup files back to their previous location using:

```
mv /tmp/Meilisearch /path/to/your/meilisearch/directory/Meilisearch mv /tmp/data.ms /path/to/your/meilisearch/directory/meilisearch/data.ms
```

```
mv /tmp/Meilisearch /usr/bin/Meilisearch mv /tmp/data.ms /var/lib/meilisearch/data.ms
```

For **cloud platforms** run the configuration script at the root of your Meilisearch directory:

```
meilisearch-setup
```

If all went well, you can delete the backup files using:

```
rm -r /tmp/Meilisearch rm -r /tmp/data.ms
```

You can also delete the dump file if desired:

```
rm /path/to/your/meilisearch/directory/meilisearch/dumps/{dump_uid.dump}
```

```
rm /var/opt/meilisearch/dumps/{dump_uid.dump}
```

## Version-specific warnings

After migrating to the most recent version of Meilisearch, your code-base may require some changes. This section contains warnings for some of the most impactful version-specific changes. For full changelogs, see the [releases tab on GitHub](https://github.com/meilisearch/meilisearch/releases).

- If you are updating from **v0.25 or below**, be aware that:
 - The `private` and `public` keys have been deprecated and replaced by two default API keys with similar permissions: `Default Admin API Key` and `Default Search API Key`.
 - The `updates` API has been replaced with the `tasks` API.
- If you are **updating from v0.27 or below**, existing keys will have their `key` and `uid` fields regenerated.
- If you are **updating from v0.30 or below to v1.0 or above on a cloud platform**, replace `--dumps-dir` with `--dump-dir` in the following files:
 - `/etc/systemd/system/meilisearch.service`
 - `/var/opt/meilisearch/scripts/first-login/001-setup-prod.sh`

---

# API Reference

## Batches

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesGetAllBatches1 from '/snippets/samples/code_samples_get_all_batches_1.mdx';
import CodeSamplesGetBatch1 from '/snippets/samples/code_samples_get_batch_1.mdx';

The `/batches` route gives information about the progress of batches of [asynchronous operations](/learn/async/asynchronous_operations).

## Batch object

```json
{
 "uid": 0,
 "progress": {
 "steps": [
 { 
 "currentStep": "extracting words",
 "finished": 2,
 "total": 9,
 },
 {
 "currentStep": "document",
 "finished": 30546,
 "total": 31944,
 }
 ],
 "percentage": 32.8471
 },
 "details": {
 "receivedDocuments": 6,
 "indexedDocuments": 6
 },
 "stats": {
 "totalNbTasks": 1,
 "status": {
 "succeeded": 1
 },
 "types": {
 "documentAdditionOrUpdate": 1
 },
 "indexUids": {
 "INDEX_NAME": 1
 }, 
 "progressTrace": { … },
 "writeChannelCongestion": { … },
 "internalDatabaseSizes": { … },
 "embedderRequests": {
 "total": 12,
 "failed": 5,
 "lastError": "runtime error: received internal error HTTP 500 from embedding server\n - server replied with `{\"error\":\"Service Unavailable\"}`"
 }
 },
 "duration": "PT0.250518S",
 "startedAt": "2024-12-10T15:20:30.18182Z",
 "finishedAt": "2024-12-10T15:20:30.432338Z",
 "batchStrategy": "batched all enqueued tasks"
}
```

### `uid`

**Type**: Integer<br />
**Description**: Unique sequential identifier of the batch. Starts at `0` and increases by one for every new batch.

### `details`

**Type**: Object<br />
**Description**: Basic information on the types tasks in a batch. Consult the [task object reference](/reference/api/tasks#details) for an exhaustive list of possible values.

### `progress`

**Type**: Object<br />
**Description**: Object containing two fields: `steps` and `percentage`. Once Meilisearch has fully processed a batch, its `progress` is set to `null`.

#### `steps`

Information about the current operations Meilisearch is performing in this batch. A step may consist of multiple substeps. | Name | Description | | :---| :--- | | **`currentStep`** | A string describing the operation | | **`total`** | The total number of operations in the step | | **`finished`** | The number of operations Meilisearch has completed | If Meilisearch is taking longer than expected to process a batch, monitor the `steps` array. If the `finished` field of the last item in the `steps` array does not update, Meilisearch may be stuck.

#### `percentage`

The percentage of completed operations, calculated from all current steps and substeps. This value is a rough estimate and may not always reflect the current state of the batch due to how different steps are processed more quickly than others.

### `stats`

**Type**: Object<br />
**Description**: Detailed information on the payload of all tasks in a batch.

#### `totalNbTasks`

Number of tasks in the batch.

#### `status`

Object listing the [status of each task](/reference/api/tasks#status) in the batch. Contains five keys whose values correspond to the number of tasks with that status.

#### `types`

List with the `types` of tasks contained in the batch.

#### `indexUids`

List of the number of tasks in the batch separated by the indexes they affect.

#### `progressTrace`

List with full paths for each operation performed in the batch, together with the processing time in human-readable format.

#### `writeChannelCongestion`

Object containing information on write operations computed during indexing. Can be useful when diagnosing performance issues associated with write speeds.

#### `internalDatabaseSizes`

Size of each internal database, including by how much it changed after a batch was processed.

#### `embedderRequests`

Object containing the total number of requests made to the embedder. Also displays the number of failed requests, if any, along with the error message for the most recent failure.

Only present in batches with at least one task querying an embedder. This field continuously updates until Meilisearch finishes processing the batch.

### `duration`

**Type**: String<br />
**Description**: The total elapsed time the batch spent in the `processing` state, in [ISO 8601](https://www.ionos.com/digitalguide/websites/web-development/iso-8601/) format. Set to `null` while the batch is processing tasks

### `startedAt`

**Type**: String<br />
**Description**: The date and time when the batch began `processing`, in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format

### `finishedAt`

**Type**: String<br />
**Description**: The date and time when the tasks finished `processing`, whether `failed`, `succeeded`, or `canceled`, in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format

### `batchStrategy`

**Type**: String<br />
**Description**: A string describing the logic behind the creation of the batch. Can contain useful information when diagnosing indexing performance issues.

## Get batches

List all batches, regardless of index. The batch objects are contained in the `results` array.

Batches are always returned in descending order of `uid`. This means that by default, **the most recently created batch objects appear first**.

Batch results are [paginated](/learn/async/paginating_tasks) and can be [filtered](/learn/async/filtering_tasks) with query parameters.

Some query parameters for `/batches`, such as `uids` and `statuses`, target tasks instead of batches.

e.g., `?uids=0` returns a batch containing the task with a `taskUid` equal to `0`, instead of a batch with a `batchUid` equal to `0`.

### Query parameters | Query Parameter | Default Value | Description | | --- | --- | --- | | **`uids`** | `*` (all task uids) | Select batches containing the tasks with the specified `uid`s. Separate multiple task `uids` with a comma (`,`) | | **`batchUids`** | `*` (all batch uids) | Filter batches by their `uid`. Separate multiple batch `uids` with a comma (`,`) | | **`indexUids`** | `*` (all indexes) | Select batches containing tasks affecting the specified indexes. Separate multiple `indexUids` with a comma (`,`) | | **`statuses`** | `*` (all statuses) | Select batches containing tasks with the specified `status`. Separate multiple task `statuses` with a comma (`,`) | | **`types`** | `*` (all types) | Select batches containing tasks with the specified `type`. Separate multiple task `types` with a comma (`,`) | | **`limit`** | `20` | Number of batches to return | | **`from`** | `uid` of the last created batch | `uid` of the first batch returned | | **`reverse`** | `false` | If `true`, returns results in the reverse order, from oldest to most recent | | **`beforeEnqueuedAt`** | `*` (all tasks) | Select batches containing tasks with the specified `enqueuedAt` field | | **`beforeStartedAt`** | `*` (all tasks) | Select batches containing tasks with the specified `startedAt` field | | **`beforeFinishedAt`** | `*` (all tasks) | Select batches containing tasks with the specified `finishedAt` field | | **`afterEnqueuedAt`** | `*` (all tasks) | Select batches containing tasks with the specified `enqueuedAt` field | | **`afterStartedAt`** | `*` (all tasks) | Select batches containing tasks with the specified `startedAt` field | | **`afterFinishedAt`** | `*` (all tasks) | Select batches containing tasks with the specified `finishedAt` field | ### Response | Name | Type | Description | | :--- | :--- | :--- | | **`results`** | Array | An array of [batch objects](#batch-object) | | **`total`** | Integer | Total number of batches matching the filter or query | | **`limit`** | Integer | Number of batches returned | | **`from`** | Integer | `uid` of the first batch returned | | **`next`** | Integer | Value passed to `from` to view the next "page" of results. When the value of `next` is `null`, there are no more tasks to view | ### Example

#### Response: `200 Ok`

```json
{
 "results": [
 {
 "uid": 2,
 "progress": null,
 "details": {
 "stopWords": [
 "of",
 "the"
 ]
 },
 "stats": {
 "totalNbTasks": 1,
 "status": {
 "succeeded": 1
 },
 "types": {
 "settingsUpdate": 1
 },
 "indexUids": {
 "INDEX_NAME": 1
 },
 "progressTrace": { … },
 "writeChannelCongestion": { … },
 "internalDatabaseSizes": { … },
 "embedderRequests": {
 "total": 12,
 "failed": 5,
 "lastError": "runtime error: received internal error HTTP 500 from embedding server\n - server replied with `{\"error\":\"Service Unavailable\"}`"
 }
 },
 "duration": "PT0.110083S",
 "startedAt": "2024-12-10T15:49:04.995321Z",
 "finishedAt": "2024-12-10T15:49:05.105404Z",
 "batchStrategy": "batched all enqueued tasks"
 }
 ],
 "total": 3,
 "limit": 1,
 "from": 2,
 "next": 1
}
```

## Get one batch

Get a single batch.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`batch_uid`** * | String | [`uid`](#uid) of the requested batch | ### Example

#### Response: `200 Ok`

```json
{
 "uid": 1,
 "details": {
 "receivedDocuments": 1,
 "indexedDocuments": 1
 },
 "progress": null,
 "stats": {
 "totalNbTasks": 1,
 "status": {
 "succeeded": 1
 },
 "types": {
 "documentAdditionOrUpdate": 1
 },
 "indexUids": {
 "INDEX_NAME": 1
 },
 "progressTrace": { … },
 "writeChannelCongestion": { … },
 "internalDatabaseSizes": { … },
 "embedderRequests": {
 "total": 12,
 "failed": 5,
 "lastError": "runtime error: received internal error HTTP 500 from embedding server\n - server replied with `{\"error\":\"Service Unavailable\"}`"
 }
 },
 "duration": "PT0.364788S",
 "startedAt": "2024-12-10T15:48:49.672141Z",
 "finishedAt": "2024-12-10T15:48:50.036929Z",
 "batchStrategy": "batched all enqueued tasks"
}
```

---

## Chats

import { RouteHighlighter } from '/snippets/route_highlighter.mdx';

The `/chats` route enables AI-powered conversational search by integrating Large Language Models (LLMs) with your Meilisearch data.

This is an experimental feature. Use the Cloud UI or the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "chatCompletions": true
 }'
```

Conversational search is still in early development. Conversational agents may occasionally hallucinate inaccurate and misleading information, so it is important to closely monitor it in production environments.

## Authorization

When implementing conversational search, use an API key with access to both the `search` and `chatCompletions` actions such as the default chat API key. You may also use tenant tokens instead of an API key, provided you generate the tokens with a key that has access to the required actions.

Chat queries only search the indexes its API key can access. The default chat API key has access to all indexes. To limit access, you must either create a new key, or [generate a tenant token](/learn/security/generate_tenant_token_sdk) from the default chat API key.

## Chat workspaces

Workspaces are groups of chat settings tailored towards specific use cases. You must configure at least on workspace to use chat completions.

### Chat workspace object

```json
{
 "uid": "WORKSPACE_NAME"
}
``` | Name | Type | Description | | :--- | :--- | :--- | | **`uid`** | String | Unique identifier for the chat completions workspace | ### Chat workspace settings object

```json
{
 "source": "PROVIDER",
 "orgId": null,
 "projectId": null,
 "apiVersion": null,
 "deploymentId": null,
 "baseUrl": null,
 "apiKey": "PROVIDER_API_KEY",
 "prompts": {
 "system": "Description of the general search context"
 }
}
```

#### `source`

**Type**: String<br />
**Default value**: N/A<br />
**Description**: Name of the chosen embeddings provider. Must be one of: `"openAi"`, `"azureOpenAi"`, `"mistral"`, `"gemini"`, or `"vLlm"`

#### `orgId`

**Type**: String<br />
**Default value**: N/A<br />
**Description**: Organization ID used to access the LLM provider. Required for Azure OpenAI, incompatible with other sources

#### `projectId`

**Type**: String<br />
**Default value**: N/A<br />
**Description**: Project ID used to access the LLM provider. Required for Azure OpenAI, incompatible with other sources

#### `apiVersion`

**Type**: String<br />
**Default value**: N/A<br />
**Description**: API version used by the LLM provider. Required for Azure OpenAI, incompatible with other sources

#### `deploymentId`

**Type**: String<br />
**Default value**: N/A<br />
**Description**: Deployment ID used by the LLM provider. Required for Azure OpenAI, incompatible with other sources

#### `baseUrl`

**Type**: String<br />
**Default value**: N/A<br />
**Description**: Base URL Meilisearch should target when sending requests to the embeddings provider. Must be the full URL preceding the `/chat/completions` fragment. Required for Azure OpenAI and vLLM

#### `apiKey`

**Type**: String<br />
**Default value**: N/A<br />
**Description**: API key to access the LLM provider. Optional for vLLM, mandatory for all other providers

#### `prompts`

**Type**: Object<br />
**Default value**: N/A<br />
**Description**: Prompts giving baseline context to the conversational agent.

The prompts object accepts the following fields:

- `prompts.system`: Default prompt giving the general usage context of the conversational search agent. Example: "You are a helpful bot answering questions on how to use Meilisearch"
- `prompts.searchDescription`: An internal description of the Meilisearch chat tools. Use it to instruct the agent on how and when to use the configured tools. Example: "Tool for retrieving relevant documents. Use it when users ask for factual information, past records, or resources that might exist in indexed content."
- `prompts.QParam`: Description of expected user input and the desired output. Example: "Users will ask about Meilisearch. Provide short and direct keyword-style queries."
- `prompts.IndexUidParam`: Instructions describing each index the agent has access to and how to use them. Example: "If user asks about code or API or parameters, use the index called `documentation`."

### List chat workspaces

List all chat workspaces. Results can be paginated by using the `offset` and `limit` query parameters.

#### Query parameters | Query parameter | Description | Default value | | :--- | :--- | :--- | | **`offset`** | Number of workspaces to skip | `0` | | **`limit`** | Number of workspaces to return | `20` | #### Response | Name | Type | Description | | :--- | :--- | :--- | | **`results`** | Array | An array of [workspaces](#chat-workspace-object) | | **`offset`** | Integer | Number of workspaces skipped | | **`limit`** | Integer | Number of workspaces returned | | **`total`** | Integer | Total number of workspaces | #### Example

```sh
 curl \
 -X GET 'MEILISEARCH_URL/chats?limit=3'
```

##### Response: `200 Ok`

```json
{
 "results": [
 { "uid": "WORKSPACE_1" },
 { "uid": "WORKSPACE_2" },
 { "uid": "WORKSPACE_3" }
 ],
 "offset": 0,
 "limit": 20,
 "total": 3
}
```

### Get one chat workspace

Get information about a workspace.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`workspace_uid`** * | String | `uid` of the requested index | #### Example

```sh
 curl \
 -X GET 'MEILISEARCH_URL/chats/WORKSPACE_UID'
```

##### Response: `200 Ok`

```json
{
 "uid": "WORKSPACE_UID"
}
```

### Get chat workspace settings

Retrieve the current settings for a chat workspace.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`workspace_uid`** | String | The workspace identifier | #### Response: `200 OK`

Returns the settings object. For security reasons, the `apiKey` field is obfuscated.

```json
{
 "source": "openAi",
 "prompts": {
 "system": "You are a helpful assistant."
 }
}
```

#### Example

[cURL example omitted]

### Create a chat workspace and update chat workspace settings

Configure the LLM provider and settings for a chat workspace.

If a workspace does not exist, querying this endpoint will create it.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`workspace_uid`** | String | The workspace identifier | #### Settings parameters | Name | Type | Description | | :--- | :--- | :--- | | [`source`](#source) | String | LLM source: `"openAi"`, `"azureOpenAi"`, `"mistral"`, `"gemini"`, or `"vLlm"` | | [`orgId`](#orgid) | String | Organization ID for the LLM provider | | [`projectId`](#projectid) | String | Project ID for the LLM provider | | [`apiVersion`](#apiversion) | String | API version for the LLM provider | | [`deploymentId`](#deploymentid) | String | Deployment ID for the LLM provider | | [`baseUrl`](#baseurl) | String | Base URL for the provider | | [`apiKey`](#apikey) | String | API key for the LLM provider | | [`prompts`](#prompts) | Object | Prompts object containing system prompts and other configuration | ##### Prompt parameters | Name | Type | Description | | :--- | :--- | :--- | | [`system]` (#prompts) | String | A prompt added to the start of the conversation to guide the LLM | | [`searchDescription`](#prompts) | String | A prompt to explain what the internal search function does | | [`searchQParam`](#prompts) | String | A prompt to explain what the `q` parameter of the search function does and how to use it | | [`searchIndexUidParam`](#prompts) | String | A prompt to explain what the `indexUid` parameter of the search function does and how to use it | #### Request body

```json
{
 "source": "openAi",
 "apiKey": "OPEN_AI_API_KEY",
 "prompts": {
 "system": "DEFAULT CHAT INSTRUCTIONS"
 }
}
```

All fields are optional. Only provided fields will be updated.

#### Response: `200 OK`

Returns the updated settings object. `apiKey` is write-only and will not be returned in the response.

#### Examples

[cURL example omitted]

### Reset chat workspace settings

Reset a chat workspace's settings to its default values.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`workspace_uid`** | String | The workspace identifier | #### Response: `200 OK`

Returns the settings object without the `apiKey` field.

```json
{
 "source": "openAi",
 "prompts": {
 "system": "You are a helpful assistant."
 }
}
```

#### Example

[cURL example omitted]

## Chat completions

After creating a workspace, you can use the chat completions API to create a conversational search agent.

### Stream chat completions

Create a chat completions stream using Meilisearch's OpenAI-compatible interface. This endpoint searches relevant indexes and generates responses based on the retrieved content.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`workspace`** | String | The chat completion workspace unique identifier (uid) | ### Request body

```json
{
 "model": "gpt-3.5-turbo",
 "messages": [
 {
 "role": "user",
 "content": "What are the main features of Meilisearch?"
 }
 ],
 "stream": true
}
``` | Name | Type | Required | Description | | :--- | :--- | :--- | :--- | | **`model`** | String | Yes | Model the agent should use when generating responses | | **`messages`** | Array | Yes | Array of [message objects](#message-object) | | **`stream`** | Boolean | No | Enable streaming responses. Must be `true` if specified | Meilisearch chat completions only supports streaming responses (`stream: true`).

### Message object | Name | Type | Description | | :--- | :--- | :--- | | **`role`** | String | Message role: `"system"`, `"user"`, or `"assistant"` | | **`content`** | String | Message content | #### `role`

Specifies the message origin: Meilisearch (`system`), the LLM provider (`assistant`), or user input (`user`)

#### `content`

String containing the message content.

### Response

The response follows the OpenAI chat completions format. For streaming responses, the endpoint returns Server-Sent Events (SSE).

#### Streaming response example

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"content":"Meilisearch"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"content":" is"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### Example

[cURL example omitted]

---

## Compact

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesCompactIndex1 from '/snippets/samples/code_samples_compact_index_1.mdx';

Index fragmentation occurs naturally as you use Meilisearch and can lead to decreased performance over time. `/compact` reorganizes the database and prunes unused space, which may lead to improved indexing and search speeds.

Cloud monitors database fragmentation and compacts indexes as needed. Self-hosted users may have to build a pipeline to periodically compact indexes and fix performance degradation.

Fragmentation is directly related to the number of indexing operations Meilisearch performs. Common indexing operations include adding and updating documents, as well as changes to index settings.

To estimate your index's fragmentation, query the `/stats` route. If the ratio between `databaseSize` and `usedDatabaseSize` is bigger than 30%, compacting your indexes may improve performance.

If you update documents in your indexes a few times per day, you may benefit from checking fragmentation and compacting your database once per week. If indexing load is very high, compacting indexes multiple times per week may be necessary to ensure optimal performance.

## Compact database

Compact the specified index.

During compaction, Meilisearch must temporarily duplicate the database. Ensure you have at least twice the current size of your database in free disk space when compacting an index.

### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_NAME",
 "status": "enqueued",
 "type": "IndexCompaction",
 "enqueuedAt": "2025-01-01T00:00:00.000000Z"
}
```

---

## Documents

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'
import { NoticeTag } from '/snippets/notice_tag.mdx';

import CodeSamplesAddOrReplaceDocuments1 from '/snippets/samples/code_samples_add_or_replace_documents_1.mdx';
import CodeSamplesAddOrUpdateDocuments1 from '/snippets/samples/code_samples_add_or_update_documents_1.mdx';
import CodeSamplesDeleteAllDocuments1 from '/snippets/samples/code_samples_delete_all_documents_1.mdx';
import CodeSamplesDeleteDocumentsByBatch1 from '/snippets/samples/code_samples_delete_documents_by_batch_1.mdx';
import CodeSamplesDeleteDocumentsByFilter1 from '/snippets/samples/code_samples_delete_documents_by_filter_1.mdx';
import CodeSamplesDeleteOneDocument1 from '/snippets/samples/code_samples_delete_one_document_1.mdx';
import CodeSamplesGetDocuments1 from '/snippets/samples/code_samples_get_documents_1.mdx';
import CodeSamplesGetDocumentsPost1 from '/snippets/samples/code_samples_get_documents_post_1.mdx';
import CodeSamplesGetOneDocument1 from '/snippets/samples/code_samples_get_one_document_1.mdx';

The `/documents` route allows you to create, manage, and delete documents.

[Learn more about documents.](/learn/getting_started/documents)

## Get documents with POST

Get a set of documents.

Use `offset` and `limit` to browse through documents.

`filter` will not work without first explicitly adding attributes to the [`filterableAttributes` list](/reference/api/settings#update-filterable-attributes). [Learn more about filters in our dedicated guide.](/learn/filtering_and_sorting/filter_search_results)

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Body | Name | Type | Default Value | Description | | :--- | :--- | :--- | :--- | | **`offset`** | Integer | `0` | Number of documents to skip | | **`limit`** | Integer | `20` | Number of documents to return | | **`fields`** | Array of strings/`null` | `*` | Document attributes to show (case-sensitive, comma-separated) | | **`filter`** | String/Array of array of strings/`null` | N/A | Refine results based on attributes in the `filterableAttributes` list | | **`retrieveVectors`** | Boolean | `false` | Return document vector data with search result | | **`sort`** | `null` | A list of attributes written as an array or as a comma-separated string | | **`ids`** | Array of primary keys | `null` | Return documents based on their primary keys | Sending an empty payload (`--data-binary '{}'`) will return all documents in the index.

### Response | Name | Type | Description | | :--- | :--- | :--- | | **`results`** | Array | An array of documents | | **`offset`** | Integer | Number of documents skipped | | **`limit`** | Integer | Number of documents returned | | **`total`** | Integer | Total number of documents in the index | #### Returned document order

`/indexes/{index_uid}/documents/fetch` and `/indexes/{index_uid}/documents` responses do not return documents following the order of their primary keys.

### Example

#### Response: `200 Ok`

```json
{
 "results": [
 {
 "title": "The Travels of Ibn Battuta",
 "genres": [
 "Travel",
 "Adventure"
 ],
 "language": "English",
 "rating": 4.5
 },
 {
 "title": "Pride and Prejudice",
 "genres": [
 "Classics",
 "Fiction",
 "Romance",
 "Literature"
 ],
 "language": "English",
 "rating": 4
 },
 …
 ],
 "offset": 0,
 "limit": 3,
 "total": 5
}
```

## Get documents with GET

This endpoint will be deprecated in the near future. Consider using POST `/indexes/{index_uid}/documents/fetch` instead.

Get a set of documents.

Using the query parameters `offset` and `limit`, you can browse through all your documents.`filter` must be a string. To create [filter expressions](/learn/filtering_and_sorting/filter_expression_reference) use `AND` or `OR`.

`filter` will not work without first explicitly adding attributes to the [`filterableAttributes` list](/reference/api/settings#update-filterable-attributes). [Learn more about filters in our dedicated guide.](/learn/filtering_and_sorting/filter_search_results)

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Query parameters | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`offset`** | `0` | Number of documents to skip | | **`limit`** | `20` | Number of documents to return | | **`fields`** | `*` | Document attributes to show (case-sensitive, comma-separated) | | **`filter`** | N/A | Refine results based on attributes in the `filterableAttributes` list | | **`retrieveVectors`** | `false` | Return document vector data with search result | | **`sort`** | `null` | A list of comma-separated attributes | | **`ids`** | `null` | Return documents based on their primary keys | ### Response | Name | Type | Description | | :--- | :--- | :--- | | **`results`** | Array | An array of documents | | **`offset`** | Integer | Number of documents skipped | | **`limit`** | Integer | Number of documents returned | | **`total`** | Integer | Total number of documents in the index | #### Returned document order

`/indexes/{index_uid}/documents/fetch` and `/indexes/{index_uid}/documents` responses do not return documents following the order of their primary keys.

### Example

#### Response: `200 Ok`

```json
{
 "results": [
 {
 "id": 364,
 "title": "Batman Returns",
 "overview": "While Batman deals with a deformed man calling himself the Penguin, an employee of a corrupt businessman transforms into the Catwoman.",
 "genres": [
 "Action",
 "Fantasy"
 ],
 "poster": "https://image.tmdb.org/t/p/w500/jKBjeXM7iBBV9UkUcOXx3m7FSHY.jpg",
 "release_date": 708912000
 },
 {
 "id": 13851,
 "title": " Batman: Gotham Knight",
 "overview": "A collection of key events mark Bruce Wayne's life as he journeys from beginner to Dark Knight.",
 "genres": [
 "Animation",
 "Action",
 "Adventure"
 ],
 "poster": "https://image.tmdb.org/t/p/w500/f3xUrqo7yEiU0guk2Ua3Znqiw6S.jpg",
 "release_date": 1215475200
 }
 ],
 "offset": 0,
 "limit": 2,
 "total": 5403
}
```

## Get one document

Get one document using its unique id.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | | **`document_id`** * | String/Integer | [Document id](/learn/getting_started/primary_key#document-id) of the requested document | ### Query parameters | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`fields`** | `*` | Document attributes to show (case-sensitive, comma-separated) | | **`retrieveVectors`** | `false` | Return document vector data with search result | ### Example

#### Response: `200 Ok`

```json
{
 "id": 25684,
 "title": "American Ninja 5",
 "poster": "https://image.tmdb.org/t/p/w1280/iuAQVI4mvjI83wnirpD8GVNRVuY.jpg",
 "release_date": "1993-01-01"
}
```

## Add or replace documents

Add an array of documents or replace them if they already exist. If the provided index does not exist, it will be created.

If you send an already existing document (same [document id](/learn/getting_started/primary_key#document-id)) the **whole existing document** will be overwritten by the new document. Fields that are no longer present in the new document are removed. For a partial update of the document see the [add or update documents](/reference/api/documents#add-or-update-documents) endpoint.

This endpoint accepts the following content types:

- `application/json`
- `application/x-ndjson`
- `text/csv`

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Query parameters | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`primaryKey`** | `null` | [Primary key](/learn/getting_started/primary_key#primary-field) of the index | | **`csvDelimiter`** | `","` | Configure the character separating CSV fields. Must be a string containing [one ASCII character](https://www.rfc-editor.org/rfc/rfc20). | | **`customMetadata`** | `null` | An arbitrary string accessible via the [generated task object](/reference/api/tasks#custommetadata) | Configuring `csvDelimiter` and sending data with a content type other than CSV will cause Meilisearch to throw an error.

If you want to [set the primary key of your index on document addition](/learn/getting_started/primary_key#setting-the-primary-key-on-document-addition), it can only be done **the first time you add documents** to the index. After this, the `primaryKey` parameter will be ignored if given.

### Body

An array of documents. Each document is represented as a JSON object.

```json
[
 {
 "id": 287947,
 "title": "Shazam",
 "poster": "https://image.tmdb.org/t/p/w1280/xnopI5Xtky18MPhK40cZAGAOVeV.jpg",
 "overview": "A boy is given the ability to become an adult superhero in times of need with a single magic word.",
 "release_date": "2019-03-23"
 }
]
```

#### `_vectors`

`_vectors` is a special document attribute containing an object with vector embeddings for AI-powered search.

Each key of the `_vectors` object must be the name of a configured embedder and correspond to a nested object with two fields, `embeddings` and `regenerate`:

```json
[
 {
 "id": 452,
 "title": "Female Trouble",
 "overview": "Delinquent high school student Dawn Davenport runs away from home and embarks upon a life of crime.",
 "_vectors": {
 "default": {
 "embeddings": [0.1, 0.2, 0.3],
 "regenerate": false
 },
 "ollama": {
 "embeddings": [0.4, 0.12, 0.6],
 "regenerate": true
 }
 }
 }
]
```

`embeddings` is an optional field. It must be an array of numbers representing a single embedding for that document. It may also be an array of arrays of numbers representing multiple embeddings for that document. `embeddings` defaults to `null`.

`regenerate` is a mandatory field. It must be a Boolean value. If `regenerate` is `true`, Meilisearch automatically generates embeddings for that document immediately and every time the document is updated. If `regenerate` is `false`, Meilisearch keeps the last value of the embeddings on document updates.

You may also use an array shorthand to add embeddings to a document:

```json
"_vectors": {
 "default": [0.003, 0.1, 0.75]
}
```

Vector embeddings added with the shorthand are not replaced when Meilisearch generates new embeddings. The above example is equivalent to:

```json
"default": {
 "embeddings": [0.003, 0.1, 0.75],
 "regenerate": false
}
```

If the key for an embedder inside `_vectors` is empty or `null`, Meilisearch treats the document as not having any embeddings for that embedder. This document is then returned last during AI-powered searches.

### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "documentAdditionOrUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Add or update documents

Add a list of documents or update them if they already exist. If the provided index does not exist, it will be created.

If you send an already existing document (same [document id](/learn/getting_started/primary_key#document-id)) the old document will be only partially updated according to the fields of the new document. Thus, any fields not present in the new document are kept and remain unchanged.

To completely overwrite a document, check out the [add or replace documents route](/reference/api/documents#add-or-replace-documents).

If you want to set the [**primary key** of your index](/learn/getting_started/primary_key#setting-the-primary-key-on-document-addition) through this route, you may only do so **the first time you add documents** to the index. If you try to set the primary key after having added documents to the index, the task will return an error.

This endpoint accepts the following content types:

- `application/json`
- `application/x-ndjson`
- `text/csv`

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Query parameters | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`primaryKey`** | `null` | [Primary key](/learn/getting_started/primary_key#primary-field) of the documents | | **`csvDelimiter`** | `","` | Configure the character separating CSV fields. Must be a string containing [one ASCII character](https://www.rfc-editor.org/rfc/rfc20). | | **`customMetadata`** | `null` | An arbitrary string accessible via the [generated task object](/reference/api/tasks#custommetadata) | Configuring `csvDelimiter` and sending data with a content type other than CSV will cause Meilisearch to throw an error.

### Body

An array of documents. Each document is represented as a JSON object.

```json
[
 {
 "id": 287947,
 "title": "Shazam ⚡️"
 }
]
```

### Example

This document is an update of the document found in [add or replace document](/reference/api/documents#add-or-replace-documents).

The documents are matched because they have the same [primary key](/learn/getting_started/documents#primary-field) value `id: 287947`. This route will update the `title` field as it changed from `Shazam` to `Shazam ⚡️` and add the new `genres` field to that document. The rest of the document will remain unchanged.

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "documentAdditionOrUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Update documents with function 

Use a [RHAI function](https://rhai.rs/book/engine/hello-world.html) to edit one or more documents directly in Meilisearch.

This is an experimental feature. Use the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "editDocumentsByFunction": true
 }'
```

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Query parameters | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`function`** | `null` | A string containing a RHAI function | | **`filter`** | `null` | A string containing a filter expression | | **`context`** | `null` | An object with data Meilisearch should make available for the editing function | | **`customMetadata`** | `null` | An arbitrary string accessible via the [generated task object](/reference/api/tasks#custommetadata) | #### `function`

`function` must be a string with a RHAI function that Meilisearch will apply to all selected documents. By default this function has access to a single variable, `doc`, representing the document you are currently editing. This is a required field.

#### `filter`

`filter` must be a string containing a filter expression. Use `filter` when you want only to apply `function` to a subset of the documents in your database.

#### `context`

Use `context` to pass data to the `function` scope. By default a function only has access to the document it is editing.

### Example

```sh
curl \
-X POST 'MEILISEARCH_URL/indexes/INDEX_NAME/documents/edit' \
-H 'Content-Type: application/json' \
--data-binary '{
 "function": "doc.title = `${doc.title.to_upper()}`"
}'
```

## Delete all documents

Delete all documents in the specified index.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Query parameters | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`customMetadata`** | `null` | An arbitrary string accessible via the [generated task object](/reference/api/tasks#custommetadata) | ### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "documentDeletion",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Delete one document

Delete one document based on its unique id.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | | **`document_id`** * | String/Integer | [Document id](/learn/getting_started/primary_key#document-id) of the requested document | ### Query parameters | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`customMetadata`** | `null` | An arbitrary string accessible via the [generated task object](/reference/api/tasks#custommetadata) | ### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "documentDeletion",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Delete documents by filter

Delete a set of documents based on a filter.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Query parameters | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`customMetadata`** | `null` | An arbitrary string accessible via the [generated task object](/reference/api/tasks#custommetadata) | ### Body

A filter expression written as a string or array of array of strings for the documents to be deleted.

`filter` will not work without first explicitly adding attributes to the [`filterableAttributes` list](/reference/api/settings#update-filterable-attributes). [Learn more about filters in our dedicated guide.](/learn/filtering_and_sorting/filter_search_results)

```
 "filter": "rating > 3.5"
```

Sending an empty payload (`--data-binary '{}'`) will return a `bad_request` error.

### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "documentDeletion",
 "enqueuedAt": "2023-05-15T08:38:48.024551Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Delete documents by batch

Delete a set of documents based on an array of document ids.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Query parameters | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`customMetadata`** | `null` | An arbitrary string accessible via the [generated task object](/reference/api/tasks#custommetadata) | ### Body

An array of numbers containing the unique ids of the documents to be deleted.

```json
[23488, 153738, 437035, 363869]
```

### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "documentDeletion",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

---

## Dumps

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesPostDump1 from '/snippets/samples/code_samples_post_dump_1.mdx';

The `/dumps` route allows the creation of database dumps. Dumps are `.dump` files that can be used to restore Meilisearch data or migrate between different versions.

Cloud does not support the `/dumps` route.

[Learn more about dumps](/learn/data_backup/dumps).

## Create a dump

Triggers a dump creation task. Once the process is complete, a dump is created in the [dump directory](/learn/self_hosted/configure_meilisearch_at_launch#dump-directory). If the dump directory does not exist yet, it will be created.

Dump tasks take priority over all other tasks in the queue. This means that a newly created dump task will be processed as soon as the current task is finished.

[Learn more about asynchronous operations](/learn/async/asynchronous_operations).

### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": null,
 "status": "enqueued",
 "type": "dumpCreation",
 "enqueuedAt": "2022-06-21T16:10:29.217688Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task)

---

## Experimental

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesGetExperimentalFeatures1 from '/snippets/samples/code_samples_get_experimental_features_1.mdx';
import CodeSamplesUpdateExperimentalFeatures1 from '/snippets/samples/code_samples_update_experimental_features_1.mdx';

The `/experimental-features` route allows you to activate or deactivate some of Meilisearch's [experimental features](/learn/resources/experimental_features_overview).

This route is **synchronous**. This means that no task object will be returned, and any activated or deactivated features will be made available or unavailable immediately.

The experimental API route is not compatible with all experimental features. Consult the [experimental feature overview](/learn/resources/experimental_features_overview) for a compatibility list.

## Experimental features object

```json
{
 "metrics": false,
 "logsRoute": true,
 "containsFilter": false,
 "editDocumentsByFunction": false,
 "network": false,
 "chatCompletions": false,
 "multimodal": false,
 "vectorStoreSetting": false
}
``` | Name | Type | Description | | :--- | :--- | :--- | | **`metrics`** | Boolean | `true` if feature is active, `false` otherwise | | **`logsRoute`** | Boolean | `true` if feature is active, `false` otherwise | | **`containsFilter`** | Boolean | `true` if feature is active, `false` otherwise | | **`editDocumentsByFunction`** | Boolean | `true` if feature is active, `false` otherwise | | **`network`** | Boolean | `true` if feature is active, `false` otherwise | | **`chatCompletions`** | Boolean | `true` if feature is active, `false` otherwise | | **`multimodal`** | Boolean | `true` if feature is active, `false` otherwise | | **`vectorStoreSetting`** | Boolean | `true` if feature is active, `false` otherwise | ## Get all experimental features

Get a list of all experimental features that can be activated via the `/experimental-features` route and whether they are currently activated.

### Example

#### Response: `200 Ok`

```json
{
 "metrics": false,
 "logsRoute": true,
 "containsFilter": false,
 "editDocumentsByFunction": false,
 "network": false,
 "chatCompletions": false,
 "multimodal": false,
 "vectorStoreSetting": false
}
```

## Configure experimental features

Activate or deactivate experimental features.

Setting a field to `null` leaves its value unchanged.

### Body

```
{<featureName>: }
```

### Response: `200 Ok`

```json
{
 "metrics": false,
 "logsRoute": true,
 "containsFilter": false,
 "editDocumentsByFunction": false,
 "network": false,
 "multimodal": false,
 "vectorStoreSetting": false
}
```

---

## Export

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesExperimentalDeleteLogsStream1 from '/snippets/samples/code_samples_experimental_delete_logs_stream_1.mdx';

Use the `/export` route to transfer data from your origin instance to a remote target instance. This is particularly useful when migrating from your local development environment to a Cloud instance.

## Migrate database between instances

Migrate data from the origin instance to a target instance.

Migration is an additive operation. If the exported indexes already exist in the target instance, Meilisearch keeps the existing documents intact and adds the new data to the index. If the same document is present in both the target and origin, Meilisearch replaces the target documents with the new data.

### Body | Name | Type | Default value | Description | | --- | --- | --- | --- | | **`url`** * | String | `null` | The target instance's URL address. Required | | **`apiKey`** * | String | `null` | An API key with full admin access to the target instance | | **`payloadSize`** * | String | "50 MiB" | A string specifying the payload size in a human-readable format | | **`indexes`** * | Object | `null` | A set of patterns matching the indexes you want to export. Defaults to all indexes in the origin instance | #### `url`

A string pointing to a remote Meilisearch instance, including its port if necessary.

This field is required.

#### `apiKey`

A security key with `index.create`, `settings.update`, and `documents.add` permissions to a secured Meilisearch instance.

#### `payloadSize`

The maximum size of each single data payload in a human-readable format such as `"100MiB"`. Larger payloads are generally more efficient, but require significantly more powerful machines.

#### `indexes`

A set of objects whose keys correspond to patterns matching the indexes you want to export. By default, Meilisearch exports all documents across all indexes.

Meilisearch does not override any index settings by default. If the target instance contains an index with the same name as an index you're exporting, Meilisearch uses the settings in the target instance. If the index does not already exist in the target instance, Meilisearch uses the settings in the origin instance.

Each index object accepts the following fields:

- `filter`: a [filter expression](/learn/filtering_and_sorting/filter_expression_reference) defining the subset of documents to export. Optional, defaults to `null`
- `overrideSettings`: if `true`, configures indexes in the target instance with the origin instance settings. Optional, defaults to `false`

### Example

#### Response

```json
{
 "taskUid": 2,
 "indexUid": null,
 "status": "enqueued",
 "type": "export",
 "enqueuedAt": "2025-06-26T12:54:10.785864Z"
}
```

---

## Facet search

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesFacetSearch1 from '/snippets/samples/code_samples_facet_search_1.mdx';

The `/facet-search` route allows you to search for facet values. Facet search supports [prefix search](/learn/engine/prefix) and [typo tolerance](/learn/relevancy/typo_tolerance_settings). The returned hits are sorted lexicographically in ascending order.

Meilisearch does not support facet search on numbers. Convert numeric facets to strings to make them searchable.

Internally, Meilisearch represents numbers as [`float64`](https://en.wikipedia.org/wiki/Double-precision_floating-point_format). This means they lack precision and can be represented in different ways, making it difficult to search facet values effectively.

## Perform a facet search

Search for a facet value within a given facet.

This endpoint will not work without first explicitly adding attributes to the [`filterableAttributes`](/reference/api/settings#update-filterable-attributes) list. [Learn more about facets in our dedicated guide.](/learn/filtering_and_sorting/search_with_facet_filters)

Meilisearch's facet search does not support multi-word facets and only considers the first term in the`facetQuery`.

e.g., searching for `Jane` will return `Jane Austen`, but searching for `Austen` will not return `Jane Austen`.

### Body | Name | Type | Default value | Description | | --- | --- | --- | --- | | **`facetName`** * | String | `null` | Facet name to search values on | | **`facetQuery`** | String | `null` | Search query for a given facet value. If `facetQuery` isn't specified, Meilisearch returns all facet values for the searched facet, limited to 100 | | **[`q`](/reference/api/search#query-q)** | String | `""` | Query string | | **[`filter`](/reference/api/search#filter)** | [String*](/learn/filtering_and_sorting/filter_expression_reference) | `null` | Filter queries by an attribute's value | | **[`matchingStrategy`](/reference/api/search#matching-strategy)** | String | `"last"` | Strategy used to match query terms within documents | | **[`attributesToSearchOn`](/reference/api/search##customize-attributes-to-search-on-at-search-time)** | Array of strings | `null` | Restrict search to the specified attributes | | **`exhaustiveFacetCount`** | Boolean | `false` | Return an exhaustive count of facets, up to the limit defined by [`maxTotalHits`](/reference/api/settings#pagination) | ### Response | Name | Type | Description | | :--- | :--- | :--- | | **`facetHits.value`** | String | Facet value matching the `facetQuery` | | **`facetHits.count`** | Integer | Number of documents with a facet value matching `value` | | **`facetQuery`** | String | The original `facetQuery` | | **`processingTimeMs`** | Number | Processing time of the query | ### Example

#### Response: `200 Ok`

```json
{
 "facetHits": [
 {
 "value": "fiction",
 "count": 7
 }
 ],
 "facetQuery": "fiction",
 "processingTimeMs": 0
}
```

---

## Health

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesGetHealth1 from '/snippets/samples/code_samples_get_health_1.mdx';

The `/health` route allows you to verify the status and availability of a Meilisearch instance.

## Get health

Get health of Meilisearch server.

### Example

#### Response: `200 OK`

```json
{ "status": "available" }
```

---

## Indexes

import { RouteHighlighter } from '/snippets/route_highlighter.mdx';

import CodeSamplesCreateAnIndex1 from '/snippets/samples/code_samples_create_an_index_1.mdx';
import CodeSamplesDeleteAnIndex1 from '/snippets/samples/code_samples_delete_an_index_1.mdx';
import CodeSamplesGetOneIndex1 from '/snippets/samples/code_samples_get_one_index_1.mdx';
import CodeSamplesListAllIndexes1 from '/snippets/samples/code_samples_list_all_indexes_1.mdx';
import CodeSamplesSwapIndexes1 from '/snippets/samples/code_samples_swap_indexes_1.mdx';
import CodeSamplesUpdateAnIndex1 from '/snippets/samples/code_samples_update_an_index_1.mdx';

The `/indexes` route allows you to create, manage, and delete your indexes.

[Learn more about indexes](/learn/getting_started/indexes).

## Index object

```json
{
 "uid": "movies",
 "createdAt": "2022-02-10T07:45:15.628261Z",
 "updatedAt": "2022-02-21T15:28:43.496574Z",
 "primaryKey": "id"
}
``` | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`uid`** | String | N/A | [Unique identifier](/learn/getting_started/indexes#index-uid) of the index. Once created, it cannot be changed | | **`createdAt`** | String | N/A | Creation date of the index, represented in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format. Auto-generated on index creation | | **`updatedAt`** | String | N/A | Latest date of index update, represented in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format. Auto-generated on index creation or update | | **`primaryKey`** | String / `null` | `null` | [Primary key](/learn/getting_started/primary_key#primary-field) of the index. If not specified, Meilisearch [guesses your primary key](/learn/getting_started/primary_key#meilisearch-guesses-your-primary-key) from the first document you add to the index | ## List all indexes

List all indexes. Results can be paginated by using the `offset` and `limit` query parameters.

### Query parameters | Query parameter | Description | Default value | | :--- | :--- | :--- | | **`offset`** | Number of indexes to skip | `0` | | **`limit`** | Number of indexes to return | `20` | ### Response | Name | Type | Description | | :--- | :--- | :--- | | **`results`** | Array | An array of [indexes](#index-object) | | **`offset`** | Integer | Number of indexes skipped | | **`limit`** | Integer | Number of indexes returned | | **`total`** | Integer | Total number of indexes | ### Example

#### Response: `200 Ok`

```json
{
 "results": [
 {
 "uid": "books",
 "createdAt": "2022-03-08T10:00:27.377346Z",
 "updatedAt": "2022-03-08T10:00:27.391209Z",
 "primaryKey": "id"
 },
 {
 "uid": "meteorites",
 "createdAt": "2022-03-08T10:00:44.518768Z",
 "updatedAt": "2022-03-08T10:00:44.582083Z",
 "primaryKey": "id"
 },
 {
 "uid": "movies",
 "createdAt": "2022-02-10T07:45:15.628261Z",
 "updatedAt": "2022-02-21T15:28:43.496574Z",
 "primaryKey": "id"
 }
 ],
 "offset": 0,
 "limit": 3,
 "total": 5
} 
```

## Get one index

Get information about an index.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Example

#### Response: `200 Ok`

```json
{
 "uid": "movies",
 "createdAt": "2022-02-10T07:45:15.628261Z",
 "updatedAt": "2022-02-21T15:28:43.496574Z",
 "primaryKey": "id"
}
```

## Create an index

Create an index.

### Body | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`uid`** * | String | N/A | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | | **`primaryKey`** | String / `null` | `null` | [`Primary key`](/learn/getting_started/primary_key#primary-field) of the requested index | ```json
{
 "uid": "movies",
 "primaryKey": "id"
}
```

### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 0,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "indexCreation",
 "enqueuedAt": "2021-08-12T10:00:00.000000Z"
}
```

You can use the response's `taskUid` to [track the status of your request](/reference/api/tasks#get-one-task).

## Update an index

Update an index's [primary key](/learn/getting_started/primary_key#primary-key). You can freely update the primary key of an index as long as it contains no documents.

To change the primary key of an index that already contains documents, you must first delete all documents in that index. You may then change the primary key and index your dataset again.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Body | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`primaryKey`** * | String / `null` | N/A | [`Primary key`](/learn/getting_started/primary_key#primary-field) of the requested index | | **`uid`** * | String / `null` | N/A | New `uid` of the requested index | ### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "indexUpdate",
 "enqueuedAt": "2021-08-12T10:00:00.000000Z"
}
```

You can use the response's `taskUid` to [track the status of your request](/reference/api/tasks#get-one-task).

## Delete an index

Delete an index.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "indexDeletion",
 "enqueuedAt": "2021-08-12T10:00:00.000000Z"
}
```

You can use the response's `taskUid` to [track the status of your request](/reference/api/tasks#get-one-task).

## Swap indexes

Swap the documents, settings, and task history of two or more indexes. **You can only swap indexes in pairs.** A single request can swap as many index pairs as you wish.

Swapping indexes is an atomic transaction: **either all indexes in a request are successfully swapped, or none are.** You can swap multiple pairs of indexes with a single request. To do so, there must be one object for each pair of indexes to be swapped.

Swapping `indexA` and `indexB` will also replace every mention of `indexA` by `indexB` and vice-versa in the task history. `enqueued` tasks are left unmodified.

[To learn more about index swapping, refer to this short guide.](/learn/getting_started/indexes#swapping-indexes)

### Body

An array of objects with the following fields: | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`indexes`** | Array of strings | N/A | Array of the two `indexUid`s to be swapped | | **`rename`** | Boolean | `false` | If `true`, renames an index instead of swapping it | Each `indexes` array must contain only two elements: the `indexUid`s of the two indexes to be swapped. Sending an empty array (`[]`) is valid, but no swap operation will be performed.

Use `rename: false` if you are swapping two existing indexes. Use `rename: true` if the second index in your array does not exist.

### Example

#### Response

```json
{
 "taskUid": 3,
 "indexUid": null,
 "status": "enqueued",
 "type": "indexSwap",
 "enqueuedAt": "2021-08-12T10:00:00.000000Z"
}
```

Since `indexSwap` is a [global task](/learn/async/asynchronous_operations#global-tasks), the `indexUid` is always `null`.

You can use the response's `taskUid` to [track the status of your request](/reference/api/tasks#get-one-task).

---

## Keys

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesCreateAKey1 from '/snippets/samples/code_samples_create_a_key_1.mdx';
import CodeSamplesDeleteAKey1 from '/snippets/samples/code_samples_delete_a_key_1.mdx';
import CodeSamplesGetAllKeys1 from '/snippets/samples/code_samples_get_all_keys_1.mdx';
import CodeSamplesGetOneKey1 from '/snippets/samples/code_samples_get_one_key_1.mdx';
import CodeSamplesUpdateAKey1 from '/snippets/samples/code_samples_update_a_key_1.mdx';

The `/keys` route allows you to create, manage, and delete API keys. To use these endpoints, you must first [set the master key](/learn/security/basic_security). Once a master key is set, you can access these endpoints by supplying it in the header of the request, or using API keys that have access to the `keys.get`, `keys.create`, `keys.update`, or `keys.delete` actions.

Accessing the `/keys` route without setting a master key will throw a [`missing_master_key`](/reference/errors/error_codes#missing_master_key) error.

## Key object

```json
{
 "name": "Default Search API Key",
 "description": "Use it to search from the frontend code",
 "key": "0a6e572506c52ab0bd6195921575d23092b7f0c284ab4ac86d12346c33057f99",
 "uid": "74c9c733-3368-4738-bbe5-1d18a5fecb37",
 "actions": [
 "search"
 ],
 "indexes": [
 "*"
 ],
 "expiresAt": null,
 "createdAt": "2021-08-11T10:00:00Z",
 "updatedAt": "2021-08-11T10:00:00Z"
}
```

### `name`

**Type**: String<br />
**Default value**: `null`<br />
**Description**: A human-readable name for the key

### `description`

**Type**: String<br />
**Default value**: `null`<br />
**Description**: A description for the key. You can add any important information about the key here

### `uid`

**Type**: String<br />
**Default value**: N/A<br />
**Description**: A [uuid v4](https://www.sohamkamani.com/uuid-versions-explained) to identify the API key. If not specified, it is automatically generated by Meilisearch ### `key`

**Type**: String<br />
**Default value**: N/A<br />
**Description**: An alphanumeric key value generated by Meilisearch by hashing the `uid` and the master key on API key creation. Used for authorization when [making calls to a protected Meilisearch instance](/learn/security/basic_security#sending-secure-api-requests-to-meilisearch)

This value is also used as the `{key}` path variable to [update](#update-a-key), [delete](#delete-a-key), or [get](#get-one-key) a specific key.

If the master key changes, all `key` values are automatically changed.

Custom API keys are deterministic: `key` is a SHA256 hash of the `uid` and master key. To reuse custom API keys, launch the new instance with the same master key and recreate your API keys with the same `uid`.

**You cannot reuse default API keys between instances.** Meilisearch automatically generates their `uid`s the first time you launch an instance.

### `actions`

**Type**: Array<br />
**Default value**: N/A<br />
**Description**: An array of API actions permitted for the key, represented as strings. API actions are only possible on authorized [`indexes`](#indexes). `["*"]` for all actions.

You can use `*` as a wildcard to access all endpoints for the `documents`, `indexes`, `tasks`, `settings`, `stats`, `webhooks`, and `dumps` actions. e.g., `documents.*` gives access to all document actions.

For security reasons, we do not recommend creating keys that can perform all actions. | Name | Description | | :--- | :--- | | **`search`** | Provides access to both [POST](/reference/api/search#search-in-an-index-with-post) and [GET](/reference/api/search#search-in-an-index-with-get) search endpoints | | **`documents.add`** | Provides access to the [add documents](/reference/api/documents#add-or-replace-documents) and [update documents](/reference/api/documents#add-or-update-documents) endpoints | | **`documents.get`** | Provides access to the [get one document](/reference/api/documents#get-one-document), [get documents with POST](/reference/api/documents#get-documents-with-post), and [get documents with GET](/reference/api/documents#get-documents-with-get) endpoints | | **`documents.delete`** | Provides access to the [delete one document](/reference/api/documents#delete-one-document), [delete all documents](/reference/api/documents#delete-all-documents), [batch delete](/reference/api/documents#delete-documents-by-batch), and [delete by filter](/reference/api/documents#delete-documents-by-filter) endpoints | | **`indexes.create`** | Provides access to the [create index](/reference/api/indexes#create-an-index) endpoint | | **`indexes.get`** | Provides access to the [get one index](/reference/api/indexes#get-one-index) and [list all indexes](/reference/api/indexes#list-all-indexes) endpoints. **Non-authorized `indexes` will be omitted from the response** | | **`indexes.update`** | Provides access to the [update index](/reference/api/indexes#update-an-index) endpoint | | **`indexes.delete`** | Provides access to the [delete index](/reference/api/indexes#delete-an-index) endpoint | | **`indexes.swap`** | Provides access to the swap indexes endpoint. **Non-authorized `indexes` will not be swapped** | | **`tasks.get`** | Provides access to the [get one task](/reference/api/tasks#get-one-task) and [get tasks](/reference/api/tasks#get-tasks) endpoints. **Tasks from non-authorized `indexes` will be omitted from the response** | | **`tasks.cancel`** | Provides access to the [cancel tasks](/reference/api/tasks#cancel-tasks) endpoint. **Tasks from non-authorized `indexes` will not be canceled** | | **`tasks.delete`** | Provides access to the [delete tasks](/reference/api/tasks#delete-tasks) endpoint. **Tasks from non-authorized `indexes` will not be deleted** | | **`settings.get`** | Provides access to the [get settings](/reference/api/settings#get-settings) endpoint and equivalents for all subroutes | | **`settings.update`** | Provides access to the [update settings](/reference/api/settings#update-settings) and [reset settings](/reference/api/settings#reset-settings) endpoints and equivalents for all subroutes | | **`stats.get`** | Provides access to the [get stats of an index](/reference/api/stats#get-stats-of-an-index) endpoint and the [get stats of all indexes](/reference/api/stats#get-stats-of-all-indexes) endpoint. For the latter, **non-authorized `indexes` are omitted from the response** | | **`dumps.create`** | Provides access to the [create dump](/reference/api/dump#create-a-dump) endpoint. **Not restricted by `indexes`** | | **`snapshots.create`** | Provides access to the [create snapshot](/reference/api/snapshots#create-a-snapshot) endpoint. **Not restricted by `indexes`** | | **`version`** | Provides access to the [get Meilisearch version](/reference/api/version#get-version-of-meilisearch) endpoint | | **`keys.get`** | Provides access to the [get all keys](#get-all-keys) endpoint | | **`keys.create`** | Provides access to the [create key](#create-a-key) endpoint | | **`keys.update`** | Provides access to the [update key](#update-a-key) endpoint | | **`keys.delete`** | Provides access to the [delete key](#delete-a-key) endpoint | | **`network.get`** | Provides access to the [get the network object](/reference/api/network#get-the-network-object) endpoint | | **`network.update`** | Provides access to the [update the network object](/reference/api/network#update-the-network-object) endpoint | | **`chatCompletions`** | Provides access to the [chat completions endpoints](/reference/api/chats). Requires experimental feature to be enabled | | **`webhooks.get`** | Provides access to the [get webhooks](/reference/api/webhooks#get-all-webhooks) endpoints | | **`webhooks.create`** | Provides access to the [create webhooks](/reference/api/webhooks#create-a-webhook) endpoint | | **`webhooks.update`** | Provides access to the [update webhooks](/reference/api/webhooks#update-a-webhook) endpoint | | **`webhooks.delete`** | Provides access to the [delete webhooks](/reference/api/webhooks#delete-a-webhook) endpoint | ### `indexes`

**Type**: Array<br />
**Default value**: N/A<br />
**Description**: An array of indexes the key is authorized to act on. Use`["*"]` for all indexes. Only the key's [permitted actions](#actions) can be used on these indexes.

You can also use the `*` character as a wildcard by adding it at the end of a string. This allows an API key access to all index names starting with that string. e.g., using `"indexes": ["movie*"]` will give the API key access to the `movies` and `movie_ratings` indexes.

### `expiresAt`

**Type**: String<br />
**Default value**: N/A<br />
**Description**: Date and time when the key will expire, represented in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format. `null` if the key never expires

Once a key is past its `expiresAt` date, using it for API authorization will return an error.

### `createdAt`

**Type**: String<br />
**Default value**: `null`<br />
**Description**: Date and time when the key was created, represented in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format

### `updatedAt`

**Type**: String<br />
**Default value**: `null`<br />
**Description**: Date and time when the key was last updated, represented in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format

## Get all keys

Returns the 20 most recently created keys in a `results` array. **Expired keys are included in the response**, but deleted keys are not.

### Query parameters

Results can be paginated using the `offset` and `limit` query parameters. | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`offset`** | `0` | Number of keys to skip | | **`limit`** | `20` | Number of keys to return | ### Response | Name | Type | Description | | :--- | :--- | :--- | | **`results`** | Array | An array of [key objects](#key-object) | | **`offset`** | Integer | Number of keys skipped | | **`limit`** | Integer | Number of keys returned | | **`total`** | Integer | Total number of API keys | ### Example

#### Response: `200 Ok`

```json
{
 "results": [
 {
 "name": null,
 "description": "Manage documents: Products/Reviews API key",
 "key": "d0552b41536279a0ad88bd595327b96f01176a60c2243e906c52ac02375f9bc4",
 "uid": "6062abda-a5aa-4414-ac91-ecd7944c0f8d",
 "actions": [
 "documents.add",
 "documents.delete"
 ],
 "indexes": [
 "prod*",
 "reviews"
 ],
 "expiresAt": "2021-12-31T23:59:59Z",
 "createdAt": "2021-10-12T00:00:00Z",
 "updatedAt": "2021-10-13T15:00:00Z"
 },
 {
 "name": "Default Search API Key",
 "description": "Use it to search from the frontend code",
 "key": "0a6e572506c52ab0bd6195921575d23092b7f0c284ab4ac86d12346c33057f99",
 "uid": "74c9c733-3368-4738-bbe5-1d18a5fecb37",
 "actions": [
 "search"
 ],
 "indexes": [
 "*"
 ],
 "expiresAt": null,
 "createdAt": "2021-08-11T10:00:00Z",
 "updatedAt": "2021-08-11T10:00:00Z"
 },
 {
 "name": "Default Admin API Key",
 "description": "Use it for anything i.e. not a search operation. Caution! Do not expose it on a public frontend",
 "key": "380689dd379232519a54d15935750cc7625620a2ea2fc06907cb40ba5b421b6f",
 "uid": "20f7e4c4-612c-4dd1-b783-7934cc038213",
 "actions": [
 "*"
 ],
 "indexes": [
 "*"
 ],
 "expiresAt": null,
 "createdAt": "2021-08-11T10:00:00Z",
 "updatedAt": "2021-08-11T10:00:00Z"
 }
 ],
 "offset": 0,
 "limit": 3,
 "total": 7
}
```

API keys are displayed in descending order based on their `createdAt` date. This means that the most recently created keys appear first.

## Get one key

Get information on the specified key. Attempting to use this endpoint with a non-existent or deleted key will result in [an error](/reference/errors/error_codes#api_key_not_found).

### Path parameters

 A valid API `key` or `uid` is required. | Name | Type | Description | | :--- | :--- | :--- | | **`key`** * | String | [`key`](#key) value of the requested API key | | **`uid`** * | String | [`uid`](#uid) of the requested API key | ### Example

#### Response: `200 Ok`

```json
{
 "name": null,
 "description": "Add documents: Products API key",
 "key": "d0552b41536279a0ad88bd595327b96f01176a60c2243e906c52ac02375f9bc4",
 "uid": "6062abda-a5aa-4414-ac91-ecd7944c0f8d",
 "actions": [
 "documents.add"
 ],
 "indexes": [
 "products"
 ],
 "expiresAt": "2021-11-13T00:00:00Z",
 "createdAt": "2021-11-12T10:00:00Z",
 "updatedAt": "2021-11-12T10:00:00Z"
}
```

For an explanation of these fields, see the [key object](#key-object).

## Create a key

Create an API key with the provided description, permissions, and expiration date.

### Body | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **[`actions`](#actions)** * | Array | N/A | A list of API actions permitted for the key. `["*"]` for all actions | | **[`indexes`](#indexes)** * | Array | N/A | An array of indexes the key is authorized to act on. `["*"]` for all indexes | | **[`expiresAt`](#expiresat)** * | String | N/A | Date and time when the key will expire, represented in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format. `null` if the key never expires | | **[`name`](#name)** | String | `null` | A human-readable name for the key | | **[`uid`](#uid)** | String | N/A | A [uuid v4](https://www.sohamkamani.com/uuid-versions-explained) to identify the API key. If not specified, it is generated by Meilisearch | | **[`description`](#description)** | String | `null` | An optional description for the key | ### Example

#### Response: `201 Created`

```json
{
 "name": null,
 "description": "Manage documents: Products/Reviews API key",
 "key": "d0552b41536279a0ad88bd595327b96f01176a60c2243e906c52ac02375f9bc4",
 "uid": "6062abda-a5aa-4414-ac91-ecd7944c0f8d",
 "actions": [
 "documents.add"
 ],
 "indexes": [
 "products"
 ],
 "expiresAt": "2021-11-13T00:00:00Z",
 "createdAt": "2021-11-12T10:00:00Z",
 "updatedAt": "2021-11-12T10:00:00Z"
}
```

## Update a key

Update the `name` and `description` of an API key.

Updates to keys are **partial**. This means you should provide only the fields you intend to update, as any fields not present in the payload will remain unchanged.

### Path parameters

 A valid API `key` or `uid` is required. | Name | Type | Description | | :--- | :--- | :--- | | **`key`** * | String | [`key`](#key) value of the requested API key | | **`uid`** * | String | [`uid`](#uid) of the requested API key | ### Body | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **[`name`](#name)** | String | `null` | A human-readable name for the key | | **[`description`](#description)** | String | `null` | An optional description for the key | ### Example

#### Response: `200 Ok`

```json
{
 "name": "Products/Reviews API key",
 "description": "Manage documents: Products/Reviews API key",
 "key": "d0552b41536279a0ad88bd595327b96f01176a60c2243e906c52ac02375f9bc4",
 "uid": "6062abda-a5aa-4414-ac91-ecd7944c0f8d",
 "actions": [
 "documents.add",
 "documents.delete"
 ],
 "indexes": [
 "products",
 "reviews"
 ],
 "expiresAt": "2021-12-31T23:59:59Z",
 "createdAt": "2021-10-12T00:00:00Z",
 "updatedAt": "2021-10-13T15:00:00Z"
}
```

## Delete a key

Delete the specified API key.

### Path parameters

 A valid API `key` or `uid` is required. | Name | Type | Description | | :--- | :--- | :--- | | **`key`** * | String | [`key`](#key) value of the requested API key | | **`uid`** * | String | [`uid`](#uid) of the requested API key | ### Example

#### Response: `204 No Content`

---

## Log customization

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesExperimentalDeleteLogsStream1 from '/snippets/samples/code_samples_experimental_delete_logs_stream_1.mdx';
import CodeSamplesExperimentalPostLogsStderr1 from '/snippets/samples/code_samples_experimental_post_logs_stderr_1.mdx';
import CodeSamplesExperimentalPostLogsStream1 from '/snippets/samples/code_samples_experimental_post_logs_stream_1.mdx';

This is an experimental feature. Use the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "logsRoute": true
 }'
```

This feature is not available for Cloud users.

## Customize log levels

Customize logging levels for the default logging system.

### Body | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`target`** * | String | N/A | A string specifying one or more log type and its log level | ### Example

## Start log stream

Opens a continuous stream of logs for focused debugging sessions. The stream will continue to run indefinitely until you [interrupt](#interrupt-log-stream) it.

### Body | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`mode`** * | String | N/A | Specifies either human-readabale or JSON output | | **`target`** * | String | N/A | A string specifying one or more log type and its log level | ## Example

Certain HTTP clients such as `httpie` and `xh`, will only display data after you have interrupted the stream with the DELETE endpoint.

## Interrupt log stream

Interrupt a log stream.

## Example

---

## Metrics

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesExperimentalGetMetrics1 from '/snippets/samples/code_samples_experimental_get_metrics_1.mdx';

The `/metrics` route exposes data compatible with [Prometheus](https://prometheus.io/). You will also need to have Grafana installed in your system to make use of this feature.

This is an experimental feature. Use the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "metrics": true
 }'
```

This feature is not available for Cloud users.

## Exposed information

`/metrics` exposes the following information: | Name | Description | Type | |---|---|---| | `meilisearch_http_requests_total` | Returns the number of times an API resource is accessed. | counter | | `meilisearch_http_response_time_seconds` | Returns a time histogram showing the number of times an API resource call goes into a time bucket (expressed in second). | histogram | | `meilisearch_db_size_bytes` | Returns the “real” size of the database on disk in bytes. It includes all the lmdb memory mapped files plus all the files contained in the `data.ms` directory (mainly the updates files that were not processed yet). | gauge | | `meilisearch_used_db_size_bytes` | Returns the size of the database actually used by Meilisearch in bytes. Include all the same files as `meilisearch_db_size_bytes` except that when it comes to an LMDB database, we only count the pages used by meilisearch. This means if you see a large gap between both metrics, adding documents will probably re-use freed pages instead of growing `meilisearch_db_size_bytes`. | gauge | | `meilisearch_index_docs_count` | Returns the number of documents for an index. | gauge | | `meilisearch_index_count` | Returns the total number of index for the Meilisearch instance. | gauge | | `meilisearch_nb_tasks` | Returns the total number of tasks for the Meilisearch instance parametrized by the kind of task and its value (see the table below). | counter | | `meilisearch_last_update` | Returns the timestamp of the last update. | gauge | | `meilisearch_is_indexing` | Returns `1` if Meilisearch is indexing or `0` if not. | gauge | API keys with access to `/metrics` are able to see all HTTP calls for all the routes in an instance. This may lead to leaking sensitive information such as index names, document's primary keys, and API keys.

## Get metrics

Get data for current status of your instance. In most cases, you should only query this endpoint via a Prometheus-compatible tool such as Grafana.

Refer to Meilisearch's sample configuration files e.g. of a [basic Prometheus scraper](https://github.com/orgs/meilisearch/discussions/assets/prometheus-basic-scraper.yml) and [Grafana dashboard](https://github.com/meilisearch/meilisearch/blob/main/assets/grafana-dashboard.json).

### Example

#### Response: `200 OK`

```
# HELP meilisearch_db_size_bytes Meilisearch DB Size In Bytes
# TYPE meilisearch_db_size_bytes gauge
meilisearch_db_size_bytes 188416
# HELP meilisearch_http_response_time_seconds Meilisearch HTTP response times
# TYPE meilisearch_http_response_time_seconds histogram
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="0.005"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="0.01"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="0.025"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="0.05"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="0.075"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="0.1"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="0.25"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="0.5"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="0.75"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="1"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="2.5"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="5"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="7.5"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="10"} 0
meilisearch_http_response_time_seconds_bucket{method="GET",path="/metrics",le="+Inf"} 0
meilisearch_http_response_time_seconds_sum{method="GET",path="/metrics"} 0
meilisearch_http_response_time_seconds_count{method="GET",path="/metrics"} 0
# HELP meilisearch_index_count Meilisearch Index Count
# TYPE meilisearch_index_count gauge
meilisearch_index_count 1
# HELP meilisearch_index_docs_count Meilisearch Index Docs Count
# TYPE meilisearch_index_docs_count gauge
meilisearch_index_docs_count{index="books"} 6
# HELP meilisearch_is_indexing Meilisearch Is Indexing
# TYPE meilisearch_is_indexing gauge
meilisearch_is_indexing 0
# HELP meilisearch_last_update Meilisearch Last Update
# TYPE meilisearch_last_update gauge
meilisearch_last_update 1723126669
# HELP meilisearch_nb_tasks Meilisearch Number of tasks
# TYPE meilisearch_nb_tasks gauge
meilisearch_nb_tasks{kind="indexes",value="books"} 1
meilisearch_nb_tasks{kind="statuses",value="canceled"} 0
meilisearch_nb_tasks{kind="statuses",value="enqueued"} 0
meilisearch_nb_tasks{kind="statuses",value="failed"} 0
meilisearch_nb_tasks{kind="statuses",value="processing"} 0
meilisearch_nb_tasks{kind="statuses",value="succeeded"} 1
meilisearch_nb_tasks{kind="types",value="documentAdditionOrUpdate"} 1
meilisearch_nb_tasks{kind="types",value="documentDeletion"} 0
meilisearch_nb_tasks{kind="types",value="documentEdition"} 0
meilisearch_nb_tasks{kind="types",value="dumpCreation"} 0
meilisearch_nb_tasks{kind="types",value="indexCreation"} 0
meilisearch_nb_tasks{kind="types",value="indexDeletion"} 0
meilisearch_nb_tasks{kind="types",value="indexSwap"} 0
meilisearch_nb_tasks{kind="types",value="indexUpdate"} 0
meilisearch_nb_tasks{kind="types",value="settingsUpdate"} 0
meilisearch_nb_tasks{kind="types",value="snapshotCreation"} 0
meilisearch_nb_tasks{kind="types",value="taskCancelation"} 0
meilisearch_nb_tasks{kind="types",value="taskDeletion"} 0
# HELP meilisearch_used_db_size_bytes Meilisearch Used DB Size In Bytes
# TYPE meilisearch_used_db_size_bytes gauge
meilisearch_used_db_size_bytes 90112
```

---

## Multi-search

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import { NoticeTag } from '/snippets/notice_tag.mdx';

import CodeSamplesMultiSearch1 from '/snippets/samples/code_samples_multi_search_1.mdx';
import CodeSamplesMultiSearchFederated1 from '/snippets/samples/code_samples_multi_search_federated_1.mdx';
import CodeSamplesMultiSearchRemoteFederated1 from '/snippets/samples/code_samples_multi_search_remote_federated_1.mdx';

The `/multi-search` route allows you to perform multiple search queries on one or more indexes by bundling them into a single HTTP request. Multi-search is also known as federated search.

## Perform a multi-search

Bundle multiple search queries in a single API request. Use this endpoint to search through multiple indexes at once.

### Body | Name | Type | Description | | :--- | :--- | :--- | | **`federation`** | Object | If present and not `null`, returns a single list merging all search results across all specified queries | | **`queries`** | Array of objects | Contains the list of search queries to perform. The [`indexUid`](/learn/getting_started/indexes#index-uid) search parameter is required, all other parameters are optional | If Meilisearch encounters an error when handling any of the queries in a multi-search request, it immediately stops processing the request and returns an error message. The returned message will only address the first error encountered.

#### `federation`

Use `federation` to receive a single list with all search results from all specified queries, in descending ranking score order. This is called federated search.

`federation` may optionally contain the following parameters: | Parameter | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **[`offset`](/reference/api/search#offset)** | Integer | `0` | Number of documents to skip | | **[`limit`](/reference/api/search#limit)** | Integer | `20` | Maximum number of documents returned | | **[`facetsByIndex`](#facetsbyindex)** | Object of arrays | `null` | Display facet information for the specified indexes | | **[`mergeFacets`](#mergefacets)** | Object | `null` | Display facet information for the specified indexes | If `federation` is missing or `null`, Meilisearch returns a list of multiple search result objects, with each item from the list corresponding to a search query in the request.

##### `facetsByIndex`

`facetsByIndex` must be an object. Its keys must correspond to indexes in your Meilisearch project. Each key must be associated with an array of attributes in the filterable attributes list of that index:

```json
"facetsByIndex": {
 "INDEX_A": ["ATTRIBUTE_X", "ATTRIBUTE_Y"],
 "INDEX_B": ["ATTRIBUTE_Z"]
}
```

When you specify `facetsByIndex`, multi-search responses include an extra `facetsByIndex` field. The response's `facetsByIndex` is an object with one field for each queried index:

```json
{
 "hits" [ … ],
 …
 "facetsByIndex": {
 "INDEX_A": {
 "distribution": {
 "ATTRIBUTE_X": {
 "KEY": ,
 "KEY": ,
 …
 },
 "ATTRIBUTE_Y": {
 "KEY": ,
 …
 }
 },
 "stats": {
 "KEY": {
 "min": ,
 "max": 
 }
 }
 },
 "INDEX_B": {
 …
 }
 }
}
```

##### `mergeFacets`

`mergeFacets` must be an object and may contain the following fields:

- `maxValuesPerFacet`: must be an integer. When specified, indicates the maximum number of returned values for a single facet. Defaults to the value assigned to [the `maxValuesPerFacet` index setting](/reference/api/settings#faceting)

When both `facetsByIndex` and `mergeFacets` are present and not null, facet information included in multi-search responses is merged across all queried indexes. Instead of `facetsByIndex`, the response includes two extra fields: `facetDistribution` and `facetStats`:

```json
{
 "hits": [ … ],
 …
 "facetDistribution": {
 "ATTRIBUTE": {
 "VALUE": ,
 "VALUE": 
 }
 },
 "facetStats": {
 "ATTRIBUTE": {
 "min": ,
 "max": 
 }
 }
}
```

##### Merge algorithm for federated searches

Federated search's merged results are returned in decreasing ranking score. To obtain the final list of results, Meilisearch compares with the following procedure:

1. Detailed ranking scores are normalized in the following way for both hits:
 1. Consecutive relevancy scores (related to the rules `words`, `typo`, `attribute`, `exactness` or `vector`) are grouped in a single score for each hit
 2. `sort` and `geosort` score details remain unchanged
2. Normalized detailed ranking scores are compared lexicographically for both hits:
 1. If both hits have a relevancy score, then the bigger score wins. If it is a tie, move to next step
 2. If one result has a relevancy score or a (geo)sort score, Meilisearch picks it
 3. If both results have a sort or geosort score in the same sorting direction, then Meilisearch compares the values according to the common sort direction. The result with the value that must come first according to the common sort direction wins. If it is a tie, go to the next step
 4. Compare the global ranking scores of both hits to determine which comes first, ignoring any sorting or geosorting
 5. In the case of a perfect tie, documents from the query with the lowest rank in the `queries` array are preferred.

Meilisearch considers two documents the same if:

1. They come from the same index
2. And their primary key is the same

There is no way to specify that two documents should be treated as the same across multiple indexes.

#### `queries`

`queries` must be an array of objects. Each object may contain the following search parameters: | Search parameter | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **[`federationOptions`](#federationoptions)** | Object | `null` | Configure federation settings for a specific query | | **[`indexUid`](/learn/getting_started/indexes#index-uid)** | String | N/A | `uid` of the requested index | | **[`q`](/reference/api/search#query-q)** | String | `""` | Query string | | **[`offset`](/reference/api/search#offset)** | Integer | `0` | Number of documents to skip | | **[`limit`](/reference/api/search#limit)** | Integer | `20` | Maximum number of documents returned | | **[`hitsPerPage`](/reference/api/search#number-of-results-per-page)** | Integer | `1` | Maximum number of documents returned for a page | | **[`page`](/reference/api/search#page)** | Integer | `1` | Request a specific page of results | | **[`filter`](/reference/api/search#filter)** | String | `null` | Filter queries by an attribute's value | | **[`facets`](/reference/api/search#facets)** | Array of strings | `null` | Display the count of matches per facet | | **[`distinct`](/reference/api/search#distinct-attributes-at-search-time)** | String | `null` | Restrict search to documents with unique values of specified attribute | | **[`attributesToRetrieve`](/reference/api/search#attributes-to-retrieve)** | Array of strings | `["*"]` | Attributes to display in the returned documents | | **[`attributesToCrop`](/reference/api/search#attributes-to-crop)** | Array of strings | `null` | Attributes whose values have to be cropped | | **[`cropLength`](/reference/api/search#crop-length)** | Integer | `10` | Maximum length of cropped value in words | | **[`cropMarker`](/reference/api/search#crop-marker)** | String | `"…"` | String marking crop boundaries | | **[`attributesToHighlight`](/reference/api/search#attributes-to-highlight)** | Array of strings | `null` | Highlight matching terms contained in an attribute | | **[`highlightPreTag`](/reference/api/search#highlight-tags)** | String | `"<em>"` | String inserted at the start of a highlighted term | | **[`highlightPostTag`](/reference/api/search#highlight-tags)** | String | `"</em>"` | String inserted at the end of a highlighted term | | **[`showMatchesPosition`](/reference/api/search#show-matches-position)** | Boolean | `false` | Return matching terms location | | **[`sort`](/reference/api/search#sort)** | Array of strings | `null` | Sort search results by an attribute's value | | **[`matchingStrategy`](/reference/api/search#matching-strategy)** | String | `last` | Strategy used to match query terms within documents | | **[`showRankingScore`](/reference/api/search#ranking-score)** | Boolean | `false` | Display the global ranking score of a document | | **[`showRankingScoreDetails`](/reference/api/search#ranking-score-details)** | Boolean | `false` | Adds a detailed global ranking score field | | **[`rankingScoreThreshold`](/reference/api/search#ranking-score-threshold)** | Number | `null` | Excludes results with low ranking scores | | **[`attributesToSearchOn`](/reference/api/search#customize-attributes-to-search-on-at-search-time)** | Array of strings | `["*"]` | Restrict search to the specified attributes | | **[`hybrid`](/reference/api/search#hybrid-search)** | Object | `null` | Return results based on query keywords and meaning | | **[`vector`](/reference/api/search#vector)** | Array of numbers | `null` | Search using a custom query vector | | **[`retrieveVectors`](/reference/api/search#display-_vectors-in-response)** | Boolean | `false` | Return document vector data | | **[`locales`](/reference/api/search#query-locales)** | Array of strings | `null` | Explicitly specify languages used in a query | Unless otherwise noted, search parameters for multi-search queries function exactly like [search parameters for the `/search` endpoint](/reference/api/search#search-parameters).

##### `limit`, `offset`, `hitsPerPage` and `page`

These options are not compatible with federated searches.

##### `federationOptions`

`federationOptions` must be an object. It accepts the following parameters:

- `weight`: serves as a multiplicative factor to ranking scores of search results in this specific query. If < `1.0`, the hits from this query are less likely to appear in the final results list. If > `1.0`, the hits from this query are more likely to appear in the final results list. Must be a positive floating-point number. Defaults to `1.0`
- `remote` : indicates the remote instance where Meilisearch will perform the query. Must be a string corresponding to a [remote object](/reference/api/network). Defaults to `null`

### Response

The response to `/multi-search` queries may take different shapes depending on the type of query you're making.

#### Non-federated multi-search requests | Name | Type | Description | | :--- | :--- | :--- | | **`results`** | Array of objects | Results of the search queries in the same order they were requested in | Each search result object is composed of the following fields: | Name | Type | Description | | :--- | :--- | :--- | | **`indexUid`** | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | | **`hits`** | Array of objects | Results of the query | | **`offset`** | Number | Number of documents skipped | | **`limit`** | Number | Number of documents to take | | **`estimatedTotalHits`** | Number | Estimated total number of matches | | **`totalHits`** | Number | Exhaustive total number of matches | | **`totalPages`** | Number | Exhaustive total number of search result pages | | **`hitsPerPage`** | Number | Number of results on each page | | **`page`** | Number | Current search results page | | **`facetDistribution`** | Object | **[Distribution of the given facets](/reference/api/search#facetdistribution)** | | **`facetStats`** | Object | [The numeric `min` and `max` values per facet](/reference/api/search#facetstats) | | **`processingTimeMs`** | Number | Processing time of the query | | **`query`** | String | Query originating the response | | **`requestUid`** | String | A UUID v7 identifying the search request | #### Federated multi-search requests

Federated search requests return a single object and the following fields: | Name | Type | Description | | :--- | :--- | :--- | | **`hits`** | Array of objects | Results of the query | | **`offset`** | Number | Number of documents skipped | | **`limit`** | Number | Number of documents to take | | **`estimatedTotalHits`** | Number | Estimated total number of matches | | **`semanticHitCount`** | Number | Exhaustive number of semantic search matches (only present in AI-powered searches) | | **`processingTimeMs`** | Number | Processing time of the query | | **`facetsByIndex`** | Object | [Data for facets present in the search results](#facetsbyindex) | | **`facetDistribution`** | Object | [Distribution of the given facets](#mergefacets) | | **`facetStats`** | Object | [The numeric `min` and `max` values per facet](#mergefacets) | | **`remoteErrors`** | Object | Indicates which remote requests failed and why | | **`requestUid`** | String | A UUID v7 identifying the search request | Each result in the `hits` array contains an additional `_federation` field with the following fields: | Name | Type | Description | | :--- | :--- | :--- | | **`indexUid`** | String | Index of origin for this document | | **`queriesPosition`** | Number | Array index number of the query in the request's `queries` array | | **`remote`** | String | Remote instance of origin for this document | **`weightedRankingScore`** | Number | The product of the _rankingScore of the hit and the weight of the query of origin. | ### Example

#### Non-federated multi-search

##### Response: `200 Ok`

```json
{
 "results": [
 {
 "indexUid": "movies",
 "hits": [
 {
 "id": 13682,
 "title": "Pooh's Heffalump Movie",
 …
 },
 …
 ],
 "query": "pooh",
 "processingTimeMs": 26,
 "limit": 5,
 "offset": 0,
 "estimatedTotalHits": 22,
 "requestUid": "0198e71e-47d2-7cd3-b507-1d0cc930b1f1"
 },
 {
 "indexUid": "movies",
 "hits": [
 {
 "id": 12,
 "title": "Finding Nemo",
 …
 },
 …
 ],
 "query": "nemo",
 "processingTimeMs": 5,
 "limit": 5,
 "offset": 0,
 "estimatedTotalHits": 11,
 "requestUid": "0198e71e-47d2-7cd3-b507-1d0cc930b1f1"
 },
 {
 "indexUid": "movie_ratings",
 "hits": [
 {
 "id": "Us",
 "director": "Jordan Peele",
 …
 }
 ],
 "query": "Us",
 "processingTimeMs": 0,
 "limit": 20,
 "offset": 0,
 "estimatedTotalHits": 1,
 "requestUid": "0198e71e-47d2-7cd3-b507-1d0cc930b1f1"
 }
 ]
}
```

#### Federated multi-search

##### Response: `200 Ok`

```json
{
 "hits": [
 {
 "id": 42,
 "title": "Batman returns",
 "overview": …, 
 "_federation": {
 "indexUid": "movies",
 "queriesPosition": 0
 }
 },
 {
 "comicsId": "batman-killing-joke",
 "description": …,
 "title": "Batman: the killing joke",
 "_federation": {
 "indexUid": "comics",
 "queriesPosition": 1
 }
 },
 …
 ],
 "processingTimeMs": 0,
 "limit": 20,
 "offset": 0,
 "estimatedTotalHits": 2,
 "semanticHitCount": 0,
 "requestUid": "0198e71e-47d2-7cd3-b507-1d0cc930b1f1"
}
```

#### Remote federated multi-search 

##### Response: `200 Ok`

```json
{
 "hits": [
 {
 "id": 42,
 "title": "Batman returns",
 "overview": …, 
 "_federation": {
 "indexUid": "movies",
 "queriesPosition": 0,
 "weightedRankingScore": 1.0,
 "remote": "ms-01"
 }
 },
 {
 "id": 87,
 "description": …,
 "title": "Batman: the killing joke",
 "_federation": {
 "indexUid": "movies",
 "queriesPosition": 1,
 "weightedRankingScore": 0.9848484848484849,
 "remote": "ms-00"
 }
 },
 …
 ],
 "processingTimeMs": 35,
 "limit": 5,
 "offset": 0,
 "estimatedTotalHits": 111,
 "requestUid": "0198e71e-47d2-7cd3-b507-1d0cc930b1f1",
 "remoteErrors": {
 "ms-02": {
 "message": "error sending request",
 "code": "proxy_could_not_send_request",
 "type": "system",
 "link": "https://docs.meilisearch.com/errors#proxy_could_not_make_request"
 }
 }
}
```

---

## Network

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'
import { NoticeTag } from '/snippets/notice_tag.mdx';

import CodeSamplesGetNetwork1 from '/snippets/samples/code_samples_get_network_1.mdx';
import CodeSamplesUpdateNetwork1 from '/snippets/samples/code_samples_update_network_1.mdx';

Use the `/network` route to create a network of Meilisearch instances. This is particularly useful when used together with federated search to implement horizontal database partition strategies such as sharding.

This is an experimental feature. Use the Cloud UI or the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "network": true
 }'
```

If an attribute is both:

- not on the `displayedAttributes` list
- present on the `sortableAttributes`

It is possible its value becomes publicly accessible via the `/network` endpoint.

Do not enable the `network` feature if you rely on the value of attributes not present in `displayedAttributes` to remain hidden at all times.

## The network object

```json
{
 "self": "ms-00",
 "sharding": false,
 "remotes": {
 "ms-00": {
 "url": "http://ms-1235.example.meilisearch.io",
 "searchApiKey": "Ecd1SDDi4pqdJD6qYLxD3y7VZAEb4d9j6LJgt4d6xas",
 "writeApiKey": "O2OaIHgwGuHNx9duH6kSe1YJ55Bh0dXvLhbr8FQVvr3vRVViBO"
 },
 "ms-01": {
 "url": "http://ms-4242.example.meilisearch.io",
 "searchApiKey": "hrVu-OMcjPGElK7692K7bwriBoGyHXTMvB5NmZkMKqQ",
 "writeApiKey": "bd1ldDoFlfyeoFDe8f3GVNiE8AHX86chmFuzOW7nWYUbPa7ww3"
 }
 }
}
```

### `self`

**Type**: String<br />
**Default value**: `null`<br />
**Description**: A string indicating the name of the current instance

### `sharding`

**Type**: Boolean<br />
**Default value**: `false`<br />
**Description**: A boolean indicating whether sharding should be enabled on the network

### `remotes`

**Type**: Object<br />
**Default value**: `{}`<br />
**Description**: An object containing [remote objects](#the-remote-object). The key of each remote object indicates the name of the remote instance

#### The remote object

```json
"ms-00": {
 "url": "http://ms-1235.example.meilisearch.io",
 "searchApiKey": "Ecd1SDDi4pqdJD6qYLxD3y7VZAEb4d9j6LJgt4d6xas",
 "writeApiKey": "O2OaIHgwGuHNx9duH6kSe1YJ55Bh0dXvLhbr8FQVvr3vRVViBO"
}
```

##### `url`

**Type**: String<br />
**Default value**: `null`<br />
**Description**: URL indicating the address of a Meilisearch instance. This URL does not need to be public, but must be accessible to all instances in the network. Required

##### `searchApiKey`

**Type**: String<br />
**Default value**: `null`<br />
**Description**: An API key with search permissions

##### `writeApiKey`

**Type**: String<br />
**Default value**: `null`<br />
**Description**: An API key with `documents.*` permissions

## Get the network object

Returns the current value of the instance's network object.

### Example

#### Response: `200 Ok`

```json
{
 "self": "ms-00",
 "sharding": false,
 "remotes": {
 "ms-00": {
 "url": "http://ms-1235.example.meilisearch.io",
 "searchApiKey": "Ecd1SDDi4pqdJD6qYLxD3y7VZAEb4d9j6LJgt4d6xas",
 "writeApiKey": "O2OaIHgwGuHNx9duH6kSe1YJ55Bh0dXvLhbr8FQVvr3vRVViBO"
 },
 "ms-01": {
 "url": "http://ms-4242.example.meilisearch.io",
 "searchApiKey": "hrVu-OMcjPGElK7692K7bwriBoGyHXTMvB5NmZkMKqQ",
 "writeApiKey": "bd1ldDoFlfyeoFDe8f3GVNiE8AHX86chmFuzOW7nWYUbPa7ww3"
 }
 }
}
```

## Update the network object

Update the `self` and `remotes` fields of the network object.

Updates to the network object are **partial**. Only provide the fields you intend to update. Fields not present in the payload will remain unchanged.

To reset `self`, `sharding` and `remotes` to their original value, set them to `null`. To remove a single `remote` from your network, set the value of its name to `null`.

### Body | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **[`self`](#self)** | String | `null` | The name of the current instance | | **[`sharding`](#sharding)** | Boolean| `false` | Whether sharding should be enabled on the network | | **[`remotes`](#remotes)** | String | `null` | A list of remote objects describing accessible Meilisearch instances | ### Example

#### Response: `200 Ok`

```json
{
 "self": "ms-00",
 "sharding": true,
 "remotes": {
 "ms-00": {
 "url": "http://INSTANCE_URL",
 "searchApiKey": "INSTANCE_API_KEY",
 "writeApiKey": "INSTANCE_WRITE_API_KEY"
 },
 "ms-01": {
 "url": "http://ANOTHER_INSTANCE_URL",
 "searchApiKey": "ANOTHER_INSTANCE_API_KEY",
 "writeApiKey": "ANOTHER_INSTANCE_WRITE_API_KEY"
 }
 }
}
```

---

## Overview

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesAuthorizationHeader1 from '/snippets/samples/code_samples_authorization_header_1.mdx';
import CodeSamplesUpdatingGuideCheckVersionOldAuthorizationHeader from '/snippets/samples/code_samples_updating_guide_check_version_old_authorization_header.mdx';

This reference describes the general behavior of Meilisearch's RESTful API.

If you are new to Meilisearch, check out the [getting started](/learn/self_hosted/getting_started_with_self_hosted_meilisearch).

## OpenAPI

Meilisearch OpenAPI specifications (`meilisearch-openapi.json`) are attached to the [latest release of Meilisearch](https://github.com/meilisearch/meilisearch/releases/tag/latest)

## Document conventions

This API documentation uses the following conventions:

- Curly braces (`{}`) in API routes represent path parameters, e.g., GET `/indexes/{index_uid}`
- Required fields are marked by an asterisk (`*`)
- Placeholder text is in uppercase characters with underscore delimiters, e.g., `MASTER_KEY`

## Authorization

By [providing Meilisearch with a master key at launch](/learn/security/basic_security), you protect your instance from unauthorized requests. The provided master key must be at least 16 bytes. From then on, you must include the `Authorization` header along with a valid API key to access protected routes (all routes except [`/health`](/reference/api/health).

The [`/keys`](/reference/api/keys) route can only be accessed using the master key. For security reasons, we recommend using regular API keys for all other routes.

v0.24 and below use the `X-MEILI-API-KEY: apiKey` authorization header:

[To learn more about keys and security, refer to our security tutorial.](/learn/security/basic_security)

## Pagination

Meilisearch paginates all GET routes that return multiple resources, e.g., GET `/indexes`, GET `/documents`, GET `/keys`, etc. This allows you to work with manageable chunks of data. All these routes return 20 results per page, but you can configure it using the `limit` query parameter. You can move between pages using `offset`.

All paginated responses contain the following fields: | Name | Type | Description | | :--- | :--- | :--- | | **`offset`** | Integer | Number of resources skipped | | **`limit`** | Integer | Number of resources returned | | **`total`** | Integer | Total number of resources | ### `/tasks` endpoint

Since the `/tasks` endpoint uses a different type of pagination, the response contains different fields. You can read more about it in the [tasks API reference](/reference/api/tasks#get-tasks).

## Parameters

Parameters are options you can pass to an API endpoint to modify its response. There are three main types of parameters in Meilisearch's API: request body parameters, path parameters, and query parameters.

### Request body parameters

These parameters are mandatory parts of POST, PUT, and PATCH requests. They accept a wide variety of values and data types depending on the resource you're modifying. You must add these parameters to your request's data payload.

### Path parameters

These are parameters you pass to the API in the endpoint's path. They are used to identify a resource uniquely. You can have multiple path parameters, e.g., `/indexes/{index_uid}/documents/{document_id}`.

If an endpoint does not take any path parameters, this section is not present in that endpoint's documentation.

### Query parameters

These optional parameters are a sequence of key-value pairs and appear after the question mark (`?`) in the endpoint. You can list multiple query parameters by separating them with an ampersand (`&`). The order of query parameters does not matter. They are mostly used with GET endpoints.

If an endpoint does not take any query parameters, this section is not present in that endpoint's documentation.

## Headers

### Content type

Any API request with a payload (`--data-binary`) requires a `Content-Type` header. Content type headers indicate the media type of the resource, helping the client process the response body correctly.

Meilisearch currently supports the following formats:

- `Content-Type: application/json` for JSON
- `Content-Type: application/x-ndjson` for NDJSON
- `Content-Type: text/csv` for CSV

Only the [add documents](/reference/api/documents#add-or-replace-documents) and [update documents](/reference/api/documents#add-or-update-documents) endpoints accept NDJSON and CSV. For all others, use `Content-Type: application/json`.

### Content encoding

The `Content-Encoding` header indicates the media type is compressed by a given algorithm. Compression improves transfer speed and reduces bandwidth consumption by sending and receiving smaller payloads. The `Accept-Encoding` header, instead, indicates the compression algorithm the client understands.

Meilisearch supports the following compression methods:

- `br`: uses the [Brotli](https://en.wikipedia.org/wiki/Brotli) algorithm
- `deflate`: uses the [zlib](https://en.wikipedia.org/wiki/Zlib) structure with the [deflate](https://en.wikipedia.org/wiki/DEFLATE) compression algorithm
- `gzip`: uses the [gzip](https://en.wikipedia.org/wiki/Gzip) algorithm

#### Request compression

The code sample below uses the `Content-Encoding: gzip` header, indicating that the request body is compressed using the `gzip` algorithm:

```
 cat ~/movies.json | gzip | curl -X POST 'MEILISEARCH_URL/indexes/movies/documents' --data-binary @- -H 'Content-Type: application/json' -H 'Content-Encoding: gzip'
```

#### Response compression

Meilisearch compresses a response if the request contains the `Accept-Encoding` header. The code sample below uses the `gzip` algorithm:

```
curl -sH 'Accept-encoding: gzip' 'MEILISEARCH_URL/indexes/movies/search' | gzip -
```

### Search metadata

You may use an optional `Meili-Include-Metadata` header when performing search and multi-search requests:

```
curl -X POST 'http://localhost:7700/indexes/INDEX_NAME/search' \
 -H 'Content-Type: application/json' \
 -H 'Authorization: Bearer MEILISEARCH_API_KEY' \
 -H 'Meili-Include-Metadata: true' \
 -d '{"q": ""}'
```

Cloud includes this header by default.

Responses will include a `metadata` object:

```json
{
 "hits": [ … ],
 "metadata": {
 "queryUid": "0199a41a-8186-70b3-b6e1-90e8cb582f35",
 "indexUid": "INDEX_NAME",
 "primaryKey": "INDEX_PRIMARY_KEY"
 }
}
```

`metadata` contains the following fields: | Field | Type | Description | |:---:|:---:|:---:| | `queryUid` | UUID v7 | Unique identifier for the query | | `indexUid` | String | Index identifier | | `primaryKey` | String | Primary key field name, if index has a primary key | | `remote` | String | Remote instance name, if request targets a remote instance | A search refers to a single HTTP search request. Every search request is assigned a `requestUid`. A query UID is a combination of `q` and `indexUid`.

In the context of multi-search, for any given `searchUid` there may be multiple `queryUid` values.

## Request body

The request body is data sent to the API. It is used with PUT, POST, and PATCH methods to create or update a resource. You must provide request bodies in JSON.

## Response body

Meilisearch is an **asynchronous API**. This means that in response to most write requests, you will receive a summarized version of the `task` object:

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "indexUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

See more information about [asynchronous operations](/learn/async/asynchronous_operations).

## Data types

The Meilisearch API supports [JSON data types](https://www.w3schools.com/js/js_json_datatypes.asp).

---

## Search

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'
import { NoticeTag } from '/snippets/notice_tag.mdx';

import CodeSamplesFacetedSearchWalkthroughFilter1 from '/snippets/samples/code_samples_faceted_search_walkthrough_filter_1.mdx';
import CodeSamplesGeosearchGuideFilterUsage1 from '/snippets/samples/code_samples_geosearch_guide_filter_usage_1.mdx';
import CodeSamplesGeosearchGuideFilterUsage3 from '/snippets/samples/code_samples_geosearch_guide_filter_usage_3.mdx';
import CodeSamplesGeosearchGuideSortUsage1 from '/snippets/samples/code_samples_geosearch_guide_sort_usage_1.mdx';
import CodeSamplesNegativeSearch1 from '/snippets/samples/code_samples_negative_search_1.mdx';
import CodeSamplesNegativeSearch2 from '/snippets/samples/code_samples_negative_search_2.mdx';
import CodeSamplesPhraseSearch1 from '/snippets/samples/code_samples_phrase_search_1.mdx';
import CodeSamplesSearchGet1 from '/snippets/samples/code_samples_search_get_1.mdx';
import CodeSamplesSearchParameterGuideAttributesToSearchOn1 from '/snippets/samples/code_samples_search_parameter_guide_attributes_to_search_on_1.mdx';
import CodeSamplesSearchParameterGuideCrop1 from '/snippets/samples/code_samples_search_parameter_guide_crop_1.mdx';
import CodeSamplesSearchParameterGuideCropMarker1 from '/snippets/samples/code_samples_search_parameter_guide_crop_marker_1.mdx';
import CodeSamplesSearchParameterGuideFacetStats1 from '/snippets/samples/code_samples_search_parameter_guide_facet_stats_1.mdx';
import CodeSamplesSearchParameterGuideHighlight1 from '/snippets/samples/code_samples_search_parameter_guide_highlight_1.mdx';
import CodeSamplesSearchParameterGuideHighlightTag1 from '/snippets/samples/code_samples_search_parameter_guide_highlight_tag_1.mdx';
import CodeSamplesSearchParameterGuideHitsperpage1 from '/snippets/samples/code_samples_search_parameter_guide_hitsperpage_1.mdx';
import CodeSamplesSearchParameterGuideHybrid1 from '/snippets/samples/code_samples_search_parameter_guide_hybrid_1.mdx';
import CodeSamplesSearchParameterGuideLimit1 from '/snippets/samples/code_samples_search_parameter_guide_limit_1.mdx';
import CodeSamplesSearchParameterGuideMatchingStrategy1 from '/snippets/samples/code_samples_search_parameter_guide_matching_strategy_1.mdx';
import CodeSamplesSearchParameterGuideMatchingStrategy2 from '/snippets/samples/code_samples_search_parameter_guide_matching_strategy_2.mdx';
import CodeSamplesSearchParameterGuideMatchingStrategy3 from '/snippets/samples/code_samples_search_parameter_guide_matching_strategy_3.mdx';
import CodeSamplesSearchParameterGuideOffset1 from '/snippets/samples/code_samples_search_parameter_guide_offset_1.mdx';
import CodeSamplesSearchParameterGuidePage1 from '/snippets/samples/code_samples_search_parameter_guide_page_1.mdx';
import CodeSamplesSearchParameterGuideQuery1 from '/snippets/samples/code_samples_search_parameter_guide_query_1.mdx';
import CodeSamplesSearchParameterGuideRetrieve1 from '/snippets/samples/code_samples_search_parameter_guide_retrieve_1.mdx';
import CodeSamplesSearchParameterGuideShowMatchesPosition1 from '/snippets/samples/code_samples_search_parameter_guide_show_matches_position_1.mdx';
import CodeSamplesSearchParameterGuideShowRankingScore1 from '/snippets/samples/code_samples_search_parameter_guide_show_ranking_score_1.mdx';
import CodeSamplesSearchParameterGuideShowRankingScoreDetails1 from '/snippets/samples/code_samples_search_parameter_guide_show_ranking_score_details_1.mdx';
import CodeSamplesSearchParameterGuideSort1 from '/snippets/samples/code_samples_search_parameter_guide_sort_1.mdx';
import CodeSamplesSearchParameterGuideVector1 from '/snippets/samples/code_samples_search_parameter_guide_vector_1.mdx';
import CodeSamplesSearchParameterReferenceDistinct1 from '/snippets/samples/code_samples_search_parameter_reference_distinct_1.mdx';
import CodeSamplesSearchParameterReferenceLocales1 from '/snippets/samples/code_samples_search_parameter_reference_locales_1.mdx';
import CodeSamplesSearchParameterReferenceRankingScoreThreshold1 from '/snippets/samples/code_samples_search_parameter_reference_ranking_score_threshold_1.mdx';
import CodeSamplesSearchParameterReferenceRetrieveVectors1 from '/snippets/samples/code_samples_search_parameter_reference_retrieve_vectors_1.mdx';
import CodeSamplesSearchPost1 from '/snippets/samples/code_samples_search_post_1.mdx';

Meilisearch exposes two routes to perform searches:

- A POST route: this is the preferred route when using API authentication, as it allows [preflight request](https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request) caching and better performance
- A GET route: the usage of this route is discouraged, unless you have good reason to do otherwise (specific caching abilities e.g.)

You may find exhaustive descriptions of the parameters accepted by the two routes [at the end of this article](#search-parameters).

## Search in an index with POST

Search for documents matching a specific query in the given index.

This is the preferred endpoint to perform search when an API key is required, as it allows for [preflight requests](https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request) to be cached. Caching preflight requests **considerably improves search speed**.

By default, [this endpoint returns a maximum of 1000 results](/learn/resources/known_limitations#maximum-number-of-results-per-search). If you want to scrape your database, use the [get documents endpoint](/reference/api/documents#get-documents-with-post) instead.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Body | Search Parameter | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **[`q`](#query-q)** | String | `""` | Query string | | **[`offset`](#offset)** | Integer | `0` | Number of documents to skip | | **[`limit`](#limit)** | Integer | `20` | Maximum number of documents returned | | **[`hitsPerPage`](#number-of-results-per-page)** | Integer | `1` | Maximum number of documents returned for a page | | **[`page`](#page)** | Integer | `1` | Request a specific page of results | | **[`filter`](#filter)** | String or array of strings | `null` | Filter queries by an attribute's value | | **[`facets`](#facets)** | Array of strings | `null` | Display the count of matches per facet | | **[`distinct`](#distinct-attributes-at-search-time)** | String | `null` | Restrict search to documents with unique values of specified attribute | | **[`attributesToRetrieve`](#attributes-to-retrieve)** | Array of strings | `["*"]` | Attributes to display in the returned documents | | **[`attributesToCrop`](#attributes-to-crop)** | Array of strings | `null` | Attributes whose values have to be cropped | | **[`cropLength`](#crop-length)** | Integer | `10` | Maximum length of cropped value in words | | **[`cropMarker`](#crop-marker)** | String | `"…"` | String marking crop boundaries | | **[`attributesToHighlight`](#attributes-to-highlight)** | Array of strings | `null` | Highlight matching terms contained in an attribute | | **[`highlightPreTag`](#highlight-tags)** | String | `"<em>"` | String inserted at the start of a highlighted term | | **[`highlightPostTag`](#highlight-tags)** | String | `"</em>"` | String inserted at the end of a highlighted term | | **[`showMatchesPosition`](#show-matches-position)** | Boolean | `false` | Return matching terms location | | **[`sort`](#sort)** | Array of strings | `null` | Sort search results by an attribute's value | | **[`matchingStrategy`](#matching-strategy)** | String | `last` | Strategy used to match query terms within documents | | **[`showRankingScore`](#ranking-score)** | Boolean | `false` | Display the global ranking score of a document | | **[`showRankingScoreDetails`](#ranking-score-details)** | Boolean | `false` | Adds a detailed global ranking score field | | **[`rankingScoreThreshold`](#ranking-score-threshold)** | Number | `null` | Excludes results with low ranking scores | | **[`attributesToSearchOn`](#customize-attributes-to-search-on-at-search-time)** | Array of strings | `["*"]` | Restrict search to the specified attributes | | **[`hybrid`](#hybrid-search)** | Object | `null` | Return results based on query keywords and meaning | | **[`vector`](#vector)** | Array of numbers | `null` | Search using a custom query vector | | **[`retrieveVectors`](#display-_vectors-in-response)** | Boolean | `false` | Return document and query vector data | | **[`locales`](#query-locales)** | Array of strings | `null` | Explicitly specify languages used in a query | | **[`media`](#media)** | Object | `null` | Perform AI-powered search queries with multimodal content | | **[`personalize`](#search-personalization)** | Object | `null` | Perform AI-powered searches that return different results based on a user's profile | ### Response | Name | Type | Description | | :--- | :--- | :--- | | **`hits`** | Array of objects | Results of the query | | **`offset`** | Number | Number of documents skipped | | **`limit`** | Number | Number of documents to take | | **`estimatedTotalHits`** | Number | Estimated total number of matches | | **`totalHits`** | Number | Exhaustive total number of matches | | **`semanticHitCount`** | Number | Exhaustive number of semantic search matches (only present in AI-powered searches) | | **`totalPages`** | Number | Exhaustive total number of search result pages | | **`hitsPerPage`** | Number | Number of results on each page | | **`page`** | Number | Current search results page | | **`facetDistribution`** | Object | **[Distribution of the given facets](#facetdistribution)** | | **`facetStats`** | Object | [The numeric `min` and `max` values per facet](#facetstats) | | **`processingTimeMs`** | Number | Processing time of the query | | **`query`** | String | Query originating the response | | **`requestUid`** | String | A UUID v7 identifying the search request | #### Exhaustive and estimated total number of search results

By default, Meilisearch only returns an estimate of the total number of search results in a query: `estimatedTotalHits`. This happens because Meilisearch prioritizes relevancy and performance over providing an exhaustive number of search results. When working with `estimatedTotalHits`, use `offset` and `limit` to navigate between search results.

If you require the total number of search results, use the `hitsPerPage` and `page` search parameters in your query. The response to this query replaces `estimatedTotalHits` with `totalHits` and includes an extra field with number of search results pages based on your `hitsPerPage`: `totalPages`. Using `totalHits` and `totalPages` may result in slightly reduced performance, but is recommended when creating UI elements such as numbered page selectors.

Neither `estimatedTotalHits` nor `totalHits` can exceed the limit configured in [the `maxTotalHits` index setting](/reference/api/settings#pagination).

You can [read more about pagination in our dedicated guide](/guides/front_end/pagination).

### Example

#### Response: `200 Ok`

```json
{
 "hits": [
 {
 "id": 2770,
 "title": "American Pie 2",
 "poster": "https://image.tmdb.org/t/p/w1280/q4LNgUnRfltxzp3gf1MAGiK5LhV.jpg",
 "overview": "The whole gang are back and as close as ever. They decide to get even closer by spending the summer together at a beach house. They decide to hold the biggest…",
 "release_date": 997405200
 },
 {
 "id": 190859,
 "title": "American Sniper",
 "poster": "https://image.tmdb.org/t/p/w1280/svPHnYE7N5NAGO49dBmRhq0vDQ3.jpg",
 "overview": "U.S. Navy SEAL Chris Kyle takes his sole mission—protect his comrades—to heart and becomes one of the most lethal snipers in American history. His pinpoint accuracy not only saves countless lives but also makes him a prime…",
 "release_date": 1418256000
 },
 …
 ],
 "offset": 0,
 "limit": 20,
 "estimatedTotalHits": 976,
 "processingTimeMs": 35,
 "query": "american",
 "requestUid": "0198e71e-47d2-7cd3-b507-1d0cc930b1f1"
}
```

## Search in an index with GET

Search for documents matching a specific query in the given index.

This endpoint only accepts [string filter expressions](/learn/filtering_and_sorting/filter_expression_reference).

This endpoint should only be used when no API key is required. If an API key is required, use the [POST](/reference/api/search#search-in-an-index-with-post) route instead.

By default, [this endpoint returns a maximum of 1000 results](/learn/resources/known_limitations#maximum-number-of-results-per-search). If you want to scrape your database, use the [get documents endpoint](/reference/api/documents#get-documents-with-post) instead.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Query parameters | Search Parameter | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **[`q`](#query-q)** | String | `""` | Query string | | **[`offset`](#offset)** | Integer | `0` | Number of documents to skip | | **[`limit`](#limit)** | Integer | `20` | Maximum number of documents returned | | **[`hitsPerPage`](#number-of-results-per-page)** | Integer | `1` | Maximum number of documents returned for a page | | **[`page`](#page)** | Integer | `1` | Request a specific page of results | | **[`filter`](#filter)** | String or array of strings | `null` | Filter queries by an attribute's value | | **[`facets`](#facets)** | Array of strings | `null` | Display the count of matches per facet | | **[`distinct`](#distinct-attributes-at-search-time)** | String | `null` | Restrict search to documents with unique values of specified attribute | | **[`attributesToRetrieve`](#attributes-to-retrieve)** | Array of strings | `["*"]` | Attributes to display in the returned documents | | **[`attributesToCrop`](#attributes-to-crop)** | Array of strings | `null` | Attributes whose values have to be cropped | | **[`cropLength`](#crop-length)** | Integer | `10` | Maximum length of cropped value in words | | **[`cropMarker`](#crop-marker)** | String | `"…"` | String marking crop boundaries | | **[`attributesToHighlight`](#attributes-to-highlight)** | Array of strings | `null` | Highlight matching terms contained in an attribute | | **[`highlightPreTag`](#highlight-tags)** | String | `"<em>"` | String inserted at the start of a highlighted term | | **[`highlightPostTag`](#highlight-tags)** | String | `"</em>"` | String inserted at the end of a highlighted term | | **[`showMatchesPosition`](#show-matches-position)** | Boolean | `false` | Return matching terms location | | **[`sort`](#sort)** | Array of strings | `null` | Sort search results by an attribute's value | | **[`matchingStrategy`](#matching-strategy)** | String | `last` | Strategy used to match query terms within documents | | **[`showRankingScore`](#ranking-score)** | Boolean | `false` | Display the global ranking score of a document | | **[`showRankingScoreDetails`](#ranking-score-details)** | Boolean | `false` | Adds a detailed global ranking score field | | **[`rankingScoreThreshold`](#ranking-score-threshold)** | Number | `null` | Excludes results with low ranking scores | | **[`attributesToSearchOn`](#customize-attributes-to-search-on-at-search-time)** | Array of strings | `["*"]` | Restrict search to the specified attributes | | **[`hybrid`](#hybrid-search)** | Object | `null` | Return results based on query keywords and meaning | | **[`vector`](#vector)** | Array of numbers | `null` | Search using a custom query vector | | **[`retrieveVectors`](#display-_vectors-in-response)** | Boolean | `false` | Return document and query vector data | | **[`locales`](#query-locales)** | Array of strings | `null` | Explicitly specify languages used in a query | ### Response | Name | Type | Description | | :--- | :--- | :--- | | **`hits`** | Array of objects | Results of the query | | **`offset`** | Number | Number of documents skipped | | **`limit`** | Number | Number of documents to take | | **`estimatedTotalHits`** | Number | Estimated total number of matches | | **`totalHits`** | Number | Exhaustive total number of matches | | **`totalPages`** | Number | Exhaustive total number of search result pages | | **`hitsPerPage`** | Number | Number of results on each page | | **`page`** | Number | Current search results page | | **`facetDistribution`** | Object | **[Distribution of the given facets](#facetdistribution)** | | **`facetStats`** | Object | [The numeric `min` and `max` values per facet](#facetstats) | | **`processingTimeMs`** | Number | Processing time of the query | | **`query`** | String | Query originating the response | | **`requestUid`** | String | A UUID v7 identifying the search request | ### Example

#### Response: `200 Ok`

```json
{
 "hits": [
 {
 "id": 2770,
 "title": "American Pie 2",
 "poster": "https://image.tmdb.org/t/p/w1280/q4LNgUnRfltxzp3gf1MAGiK5LhV.jpg",
 "overview": "The whole gang are back and as close as ever. They decide to get even closer by spending the summer together at a beach house. They decide to hold the biggest…",
 "release_date": 997405200
 },
 {
 "id": 190859,
 "title": "American Sniper",
 "poster": "https://image.tmdb.org/t/p/w1280/svPHnYE7N5NAGO49dBmRhq0vDQ3.jpg",
 "overview": "U.S. Navy SEAL Chris Kyle takes his sole mission—protect his comrades—to heart and becomes one of the most lethal snipers in American history. His pinpoint accuracy not only saves countless lives but also makes him a prime…",
 "release_date": 1418256000
 },
 …
 ],
 "offset": 0,
 "limit": 20,
 "estimatedTotalHits": 976,
 "processingTimeMs": 35,
 "query": "american",
 "requestUid": "0198e71e-47d2-7cd3-b507-1d0cc930b1f1"
}
```

## Search parameters

Here follows an exhaustive description of each search parameter currently available when using the search endpoint. Unless otherwise noted, all parameters are valid for the `GET /indexes/{index_uid}/search`, `POST /indexes/{index_uid}/search`, and `/multi-search` routes.

If [using the GET route to perform a search](/reference/api/search#search-in-an-index-with-get), all parameters must be **URL-encoded**.

This is not necessary when using the POST route or one of our [SDKs](/learn/resources/sdks).

### Query (q)

**Parameter**: `q`<br />
**Expected value**: Any string<br />
**Default value**: `null`

Sets the search terms.

Meilisearch only considers the first ten words of any given search query. This is necessary to deliver a [fast search-as-you-type experience](/learn/resources/known_limitations#maximum-number-of-query-words).

#### Example

You can search for films mentioning `shifu` by setting the `q` parameter:

This will give you a list of documents that contain your query terms in at least one attribute.

```json
{
 "hits": [
 {
 "id": 50393,
 "title": "Kung Fu Panda Holiday",
 "poster": "https://image.tmdb.org/t/p/w500/rV77WxY35LuYLOuQvBeD1nyWMuI.jpg",
 "overview": "The Winter Feast is Po's favorite holiday. Every year he and his father hang decorations, cook together, and serve noodle soup to the villagers. But this year Shifu informs Po that as Dragon Warrior, it is his duty to host the formal Winter Feast at the Jade Palace.",
 "release_date": 1290729600,
 "genres": [
 "Animation",
 "Family",
 "TV Movie"
 ]
 }
 ],
 "query": "shifu"
}
```

#### Query term normalization

Query terms go through a normalization process that removes [non-spacing marks](https://www.compart.com/en/unicode/category/Mn). Because of this, Meilisearch effectively ignores accents and diacritics when returning results. e.g., searching for `"sábia"` returns documents containing `"sábia"`, `"sabiá"`, and `"sabia"`.

Normalization also converts all letters to lowercase. Searching for `"Video"` returns the same results as searching for `"video"`, `"VIDEO"`, or `"viDEO"`.

#### Placeholder search

When `q` isn't specified, Meilisearch performs a **placeholder search**. A placeholder search returns all searchable documents in an index, modified by any search parameters used and sorted by that index's [custom ranking rules](/learn/relevancy/custom_ranking_rules). Since there is no query term, the [built-in ranking rules](/learn/relevancy/ranking_rules) **do not apply.**

If the index has no sort or custom ranking rules, the results are returned in the order of their internal database position.

Placeholder search is particularly useful when building a [faceted search interfaces](/learn/filtering_and_sorting/search_with_facet_filters), as it allows users to view the catalog and alter sorting rules without entering a query.

#### Phrase search

If you enclose search terms in double quotes (`"`), Meilisearch will only return documents containing those terms in the order they were given. This is called a **phrase search**.

Phrase searches are case-insensitive and ignore [soft separators such as `-`, `,`, and `:`](/learn/engine/datatypes). Using a hard separator within a phrase search effectively splits it into multiple separate phrase searches: `"Octavia.Butler"` will return the same results as `"Octavia" "Butler"`.

You can combine phrase search and normal queries in a single search request. In this case, Meilisearch will first fetch all documents with exact matches to the given phrase(s), and [then proceed with its default behavior](/learn/relevancy/relevancy).

##### Example

#### Negative search

Use the minus (`-`) operator in front of a word or phrase to exclude it from search results.

##### Example

The following query returns all documents that do not include the word "escape":

Negative search can be used together with phrase search:

### Offset

**Parameter**: `offset`<br />
**Expected value**: Any positive integer<br />
**Default value**: `0`

Sets the starting point in the search results, effectively skipping over a given number of documents.

Queries using `offset` and `limit` only return an estimate of the total number of search results.

You can [paginate search results](/guides/front_end/pagination) by making queries combining both `offset` and `limit`.

Setting `offset` to a value greater than an [index's `maxTotalHits`](/reference/api/settings#update-pagination-settings) returns an empty array.

#### Example

If you want to skip the **first** result in a query, set `offset` to `1`:

### Limit

**Parameter**: `limit`<br />
**Expected value**: Any positive integer or zero<br />
**Default value**: `20`

Sets the maximum number of documents returned by a single query.

You can [paginate search results](/guides/front_end/pagination) by making queries combining both `offset` and `limit`.

A search query cannot return more results than configured in [`maxTotalHits`](/reference/api/settings#pagination-object), even if the value of `limit` is greater than the value of `maxTotalHits`.

#### Example

If you want your query to return only **two** documents, set `limit` to `2`:

### Number of results per page

**Parameter**: `hitsPerPage`<br />
**Expected value**: Any positive integer<br />
**Default value**: `20`

Sets the maximum number of documents returned for a single query. The value configured with this parameter dictates the number of total pages: if Meilisearch finds a total of `20` matches for a query and your `hitsPerPage` is set to `5`, `totalPages` is `4`.

Queries containing `hitsPerPage` are exhaustive and do not return an `estimatedTotalHits`. Instead, the response body will include `totalHits` and `totalPages`.

If you set `hitsPerPage` to `0`, Meilisearch processes your request, but does not return any documents. In this case, the response body will include the exhaustive value for `totalHits`. The response body will also include `totalPages`, but its value will be `0`.

You can use `hitsPerPage` and `page` to [paginate search results](/guides/front_end/pagination).

`hitsPerPage` and `page` take precedence over `offset` and `limit`. If a query contains either `hitsPerPage` or `page`, any values passed to `offset` and `limit` are ignored.

`hitsPerPage` and `page` are resource-intensive options and might negatively impact search performance. This is particularly likely if [`maxTotalHits`](/reference/api/settings#pagination) is set to a value higher than its default.

#### Example

The following example returns the first 15 results for a query:

### Page

**Parameter**: `page`<br />
**Expected value**: Any positive integer<br />
**Default value**: `1`

Requests a specific results page. Pages are calculated using the `hitsPerPage` search parameter.

Queries containing `page` are exhaustive and do not return an `estimatedTotalHits`. Instead, the response body will include two new fields: `totalHits` and `totalPages`.

If you set `page` to `0`, Meilisearch processes your request, but does not return any documents. In this case, the response body will include the exhaustive values for `facetDistribution`, `totalPages`, and `totalHits`.

You can use `hitsPerPage` and `page` to [paginate search results](/guides/front_end/pagination).

`hitsPerPage` and `page` take precedence over `offset` and `limit`. If a query contains either `hitsPerPage` or `page`, any values passed to `offset` and `limit` are ignored.

`hitsPerPage` and `page` are resource-intensive options and might negatively impact search performance. This is particularly likely if [`maxTotalHits`](/reference/api/settings#pagination) is set to a value higher than its default.

#### Example

The following example returns the second page of search results:

### Filter

**Parameter**: `filter`<br />
**Expected value**: A filter expression written as a string or an array of strings<br />
**Default value**: `[]`

Uses filter expressions to refine search results. Attributes used as filter criteria must be added to the [`filterableAttributes` list](/reference/api/settings#filterable-attributes).

For more information, [read our guide on how to use filters and build filter expressions](/learn/filtering_and_sorting/filter_search_results).

#### Example

You can write a filter expression in string syntax using logical connectives:

```
"(genres = horror OR genres = mystery) AND director = 'Jordan Peele'"
```

You can write the same filter as an array:

```
[["genres = horror", "genres = mystery"], "director = 'Jordan Peele'"]
```

You can then use the filter in a search query:

#### Filtering results with `_geoRadius`, `_geoBoundingBox`, and `_geoPolygon`

If your documents contain `_geo` or `_geojson` data, you can use the following built-in filter rules to filter results according to their geographic position:

`_geoRadius` establishes a circular area based on a central point and a radius. This filter rule accepts the following parameters: `lat`, `lng`, `distance_in_meters`, `resolution`.

```json
_geoRadius(lat, lng, distance_in_meters, resolution)
```

- `lat` and `lng` should be geographic coordinates expressed as floating point numbers. 
- `distance_in_meters` indicates the radius of the area within which you want your results and should be an integer.
- `resolution` must be an integer between `3` and `1000` inclusive, and is an optional parameter. When using `_geojson` coordinates, `resolution` sets how many points Meilisearch will use to create a polygon that approximates the shape of a circle. Documents using `_geo` data ignore this parameter. Defaults to `125`. Increasing `resolution` may result in performance issues and is only necessary when dealing with large country-sized circles.

`_geoBoundingBox` establishes a rectangular area based on the coordinates for its top right and bottom left corners. This filter rule requires two arrays of geographic coordinates:

```
_geoBoundingBox([LAT, LNG], [LAT, LNG])
```

`LAT` and `LNG` should be geographic coordinates expressed as floating point numbers. The first array indicates the top right corner and the second array indicates the bottom left corner of the bounding box.

Meilisearch will throw an error if the top right corner is under the bottom left corner.

`_geoPolygon` establishes an area based on the coordinates of the specified points. This filter rule requires three arrays or more arrays of geographic coordinates and can only be used with GeoJSON documents:

```
_geoPolygon([LAT, LNG], [LAT, LNG], [LAT, LNG], …)
```

`LAT` and `LNG` should be geographic coordinates expressed as floating point numbers. If your polygon is not closed, Meilisearch will close it automatically. Closed polygons are polygons where the first and last points share the same coordinates.

Polygons cannot cross the 180th meridian. If a shape crosses the antimeridian, you must make two polygons and join them using the `AND` filter operator.

`_geoPolygon` is not compatible with documents using only `_geo` data. You must specify a `_geojson` attribute to use `_geoPolygon`.

If any parameters are invalid or missing, Meilisearch returns an [`invalid_search_filter`](/reference/errors/error_codes#invalid_search_filter) error.

### Facets

**Parameter**: `facets`<br />
**Expected value**: An array of `attribute`s or `["*"]`<br />
**Default value**: `null`
Returns the number of documents matching the current search query for each given facet. This parameter can take two values:

- An array of attributes: `facets=["attributeA", "attributeB", …]`
- An asterisk—this will return a count for all facets present in `filterableAttributes`

By default, `facets` returns a maximum of 100 facet values for each faceted field. You can change this value using the `maxValuesPerFacet` property of the [`faceting` index settings](/reference/api/settings#faceting).

When `facets` is set, the search results object includes the [`facetDistribution`](#facetdistribution) and [`facetStats`](#facetstats) fields.

If an attribute used on `facets` has not been added to the `filterableAttributes` list, it will be ignored.

#### `facetDistribution`

`facetDistribution` contains the number of matching documents distributed among the values of a given facet. Each facet is represented as an object:

```json
{
 …
 "facetDistribution": {
 "FACET_A": {
 "FACET_VALUE_X": 6,
 "FACET_VALUE_Y": 1,
 },
 "FACET_B": {
 "FACET_VALUE_Z": 3,
 "FACET_VALUE_W": 9,
 },
 },
 …
}
```

`facetDistribution` contains an object for every attribute passed to the `facets` parameter. Each object contains the returned values for that attribute and the count of matching documents with that value. Meilisearch does not return empty facets.

#### `facetStats`

`facetStats` contains the lowest (`min`) and highest (`max`) numerical values across all documents in each facet. Only numeric values are considered:

```json
{
 …
"facetStats": {
 "rating": {
 "min": 2.5,
 "max": 4.7
 }
 }
 …
}
```

If none of the matching documents have a numeric value for a facet, that facet is not included in the `facetStats` object. `facetStats` ignores string values, even if the string contains a number.

#### Example

Given a movie ratings database, the following code sample returns the number of `Batman` movies per genre along with the minimum and maximum ratings:

The response shows the facet distribution for `genres` and `rating`. Since `rating` is a numeric field, you get its minimum and maximum values in `facetStats`.

```json
{
 …
 "estimatedTotalHits": 22,
 "query": "Batman",
 "facetDistribution": {
 "genres": {
 "Action": 20,
 "Adventure": 7,
 …
 "Thriller": 3
 },
 "rating": {
 "2": 1,
 …
 "9.8": 1
 }
 },
 "facetStats": {
 "rating": {
 "min": 2.0,
 "max": 9.8
 }
 }
}
```

[Learn more about facet distribution in the faceted search guide.](/learn/filtering_and_sorting/search_with_facet_filters)

### Distinct attributes at search time

**Parameter**: `distinct`<br />
**Expected value**: An `attribute` present in the `filterableAttributes` list<br />
**Default value**: `null`

Defines one attribute in the `filterableAttributes` list as a distinct attribute. Distinct attributes indicate documents sharing the same value for the specified field are equivalent and only the most relevant one should be returned in search results.

This behavior is similar to the [`distinctAttribute` index setting](/reference/api/settings#distinct-attribute), but can be configured at search time. `distinctAttribute` acts as a default distinct attribute value you may override with `distinct`.

#### Examples

### Attributes to retrieve

**Parameter**: `attributesToRetrieve`<br />
**Expected value**: An array of `attribute`s or `["*"]`<br />
**Default value**: `["*"]`

Configures which attributes will be retrieved in the returned documents.

If no value is specified, `attributesToRetrieve` uses the [`displayedAttributes` list](/reference/api/settings#displayed-attributes), which by default contains all attributes found in the documents.

If an attribute has been removed from `displayedAttributes`, `attributesToRetrieve` will silently ignore it and the field will not appear in your returned documents.

#### Example

To get only the `overview` and `title` fields, set `attributesToRetrieve` to `["overview", "title"]`.

### Attributes to crop

**Parameter**: `attributesToCrop`<br />
**Expected value**: An array of attributes or `["*"]`<br />
**Default value**: `null`

Crops the selected fields in the returned results to the length indicated by the [`cropLength`](#crop-length) parameter. When `attributesToCrop` is set, each returned document contains an extra field called `_formatted`. This object contains the cropped version of the selected attributes.

By default, crop boundaries are marked by the ellipsis character (`…`). You can change this by using the [`cropMarker`](#crop-marker) search parameter.

Optionally, you can indicate a custom crop length for any attributes given to `attributesToCrop`: `attributesToCrop=["attributeNameA:5", "attributeNameB:9"]`. If configured, these values have priority over `cropLength`.

Instead of supplying individual attributes, you can provide `["*"]` as a wildcard: `attributesToCrop=["*"]`. This causes `_formatted` to include the cropped values of all attributes present in [`attributesToRetrieve`](#attributes-to-retrieve).

#### Cropping algorithm

Suppose you have a field containing the following string: `Donatello is a skilled and smart turtle. Leonardo is the most skilled turtle. Raphael is the strongest turtle.`

Meilisearch tries to respect sentence boundaries when cropping. e.g., if your search term is `Leonardo` and your `cropLength` is 6, Meilisearch will prioritize keeping the sentence together and return: `Leonardo is the most skilled turtle.`

If a query contains only a single search term, Meilisearch crops around the first occurrence of that term. If you search for `turtle` and your `cropLength` is 7, Meilisearch will return the first instance of that word: `Donatello is a skilled and smart turtle.`

If a query contains multiple search terms, Meilisearch centers the crop around the largest number of unique matches, giving priority to terms that are closer to each other and follow the original query order. If you search for `skilled turtle` with a `cropLength` of 6, Meilisearch will return `Leonardo is the most skilled turtle`.

If Meilisearch does not find any query terms in a field, cropping begins at the first word in that field. If you search for `Michelangelo` with a `cropLength` of 4 and this string is present in another field, Meilisearch will return `Donatello is a skilled …`.

#### Example

If you use `shifu` as a search query and set the value of the `cropLength` parameter to `5`:

You will get the following response with the **cropped text in the `_formatted` object**:

```json
{
 "id": 50393,
 "title": "Kung Fu Panda Holiday",
 "poster": "https://image.tmdb.org/t/p/w1280/gp18R42TbSUlw9VnXFqyecm52lq.jpg",
 "overview": "The Winter Feast is Po's favorite holiday. Every year he and his father hang decorations, cook together, and serve noodle soup to the villagers. But this year Shifu informs Po that as Dragon Warrior, it is his duty to host the formal Winter Feast at the Jade Palace. Po is caught between his obligations as the Dragon Warrior and his family traditions: between Shifu and Mr. Ping.",
 "release_date": 1290729600,
 "_formatted": {
 "id": 50393,
 "title": "Kung Fu Panda Holiday",
 "poster": "https://image.tmdb.org/t/p/w1280/gp18R42TbSUlw9VnXFqyecm52lq.jpg",
 "overview": "…this year Shifu informs Po…",
 "release_date": 1290729600
 }
}
```

### Crop length

**Parameter**: `cropLength`<br />
**Expected value**: A positive integer<br />
**Default value**: `10`

Configures the total number of words to appear in the cropped value when using [`attributesToCrop`](#attributes-to-crop). If `attributesToCrop` is not configured, `cropLength` has no effect on the returned results.

Query terms are counted as part of the cropped value length. If `cropLength` is set to `2` and you search for one term (e.g., `shifu`), the cropped field will contain two words in total (e.g., `"…Shifu informs…"`).

Stop words are also counted against this number. If `cropLength` is set to `2` and you search for one term (e.g., `grinch`), the cropped result may contain a stop word (e.g., `"…the Grinch…"`).

If `attributesToCrop` uses the `attributeName:number` syntax to specify a custom crop length for an attribute, that value has priority over `cropLength`.

### Crop marker

**Parameter**: `cropMarker`<br />
**Expected value**: A string<br />
**Default value**: `"…"`

Sets a string to mark crop boundaries when using the [`attributesToCrop`](#attributes-to-crop) parameter. The crop marker will be inserted on both sides of the crop. If `attributesToCrop` is not configured, `cropMarker` has no effect on the returned search results.

If `cropMarker` is set to `null` or an empty string, no markers will be included in the returned results.

Crop markers are only added where content has been removed. e.g., if the cropped text includes the first word of the field value, the crop marker will not be added to the beginning of the cropped result.

#### Example

When searching for `shifu`, you can use `cropMarker` to change the default `…`:

```json
{
 "id": 50393,
 "title": "Kung Fu Panda Holiday",
 "poster": "https://image.tmdb.org/t/p/w1280/gp18R42TbSUlw9VnXFqyecm52lq.jpg",
 "overview": "The Winter Feast is Po's favorite holiday. Every year he and his father hang decorations, cook together, and serve noodle soup to the villagers. But this year Shifu informs Po that as Dragon Warrior, it is his duty to host the formal Winter Feast at the Jade Palace. Po is caught between his obligations as the Dragon Warrior and his family traditions: between Shifu and Mr. Ping.",
 "release_date": 1290729600,
 "_formatted": {
 "id": 50393,
 "title": "Kung Fu Panda Holiday",
 "poster": "https://image.tmdb.org/t/p/w1280/gp18R42TbSUlw9VnXFqyecm52lq.jpg",
 "overview": "[…]But this year Shifu informs Po that as Dragon Warrior,[…]",
 "release_date": 1290729600
 }
}
```

### Attributes to highlight

**Parameter**: `attributesToHighlight`<br />
**Expected value**: An array of attributes or `["*"]`<br />
**Default value**: `null`

Highlights matching query terms in the specified attributes. `attributesToHighlight` only works on values of the following types: string, number, array, object.

When this parameter is set, returned documents include a `_formatted` object containing the highlighted terms.

Instead of a list of attributes, you can use `["*"]`: `attributesToHighlight=["*"]`. In this case, all the attributes present in [`attributesToRetrieve`](#attributes-to-retrieve) will be assigned to `attributesToHighlight`.

By default highlighted elements are enclosed in `<em>` and `</em>` tags. You may change this by using the [`highlightPreTag` and `highlightPostTag` search parameters](#highlight-tags).

`attributesToHighlight` also highlights terms configured as [synonyms](/reference/api/settings#synonyms) and [stop words](/reference/api/settings#stop-words).

`attributesToHighlight` will highlight matches within all attributes added to the `attributesToHighlight` array, even if those attributes are not set as [`searchableAttributes`](/learn/relevancy/displayed_searchable_attributes#searchable-fields).

#### Example

The following query highlights matches present in the `overview` attribute:

The highlighted version of the text would then be found in the `_formatted` object included in each returned document:

```json
{
 "id": 50393,
 "title": "Kung Fu Panda Holiday",
 "poster": "https://image.tmdb.org/t/p/w1280/gp18R42TbSUlw9VnXFqyecm52lq.jpg",
 "overview": "The Winter Feast is Po's favorite holiday. Every year he and his father hang decorations, cook together, and serve noodle soup to the villagers. But this year Shifu informs Po that as Dragon Warrior, it is his duty to host the formal Winter Feast at the Jade Palace. Po is caught between his obligations as the Dragon Warrior and his family traditions: between Shifu and Mr. Ping.",
 "release_date": 1290729600,
 "_formatted": {
 "id": 50393,
 "title": "Kung Fu Panda Holiday",
 "poster": "https://image.tmdb.org/t/p/w1280/gp18R42TbSUlw9VnXFqyecm52lq.jpg",
 "overview": "The <em>Winter Feast</em> is Po's favorite holiday. Every year he and his father hang decorations, cook together, and serve noodle soup to the villagers. But this year Shifu informs Po that as Dragon Warrior, it is his duty to host the formal <em>Winter Feast</em> at the Jade Palace. Po is caught between his obligations as the Dragon Warrior and his family traditions: between Shifu and Mr. Ping.",
 "release_date": 1290729600
 }
}
```

### Highlight tags

**Parameters**: `highlightPreTag` and `highlightPostTag`<br />
**Expected value**: A string<br />
**Default value**: `"<em>"` and `"</em>"` respectively

`highlightPreTag` and `highlightPostTag` configure, respectively, the strings to be inserted before and after a word highlighted by `attributesToHighlight`. If `attributesToHighlight` has not been configured, `highlightPreTag` and `highlightPostTag` have no effect on the returned search results.

It is possible to use `highlightPreTag` and `highlightPostTag` to enclose terms between any string of text, not only HTML tags: `"<em>"`, `"<strong>"`, `"*"`, and `"__"` are all equally supported values.

If `highlightPreTag` or `highlightPostTag` are set to `null` or an empty string, nothing will be inserted respectively at the beginning or the end of a highlighted term.

#### Example

The following query encloses highlighted matches in `<span>` tags with a `class` attribute:

You can find the highlighted query terms inside the `_formatted` property:

```json
{
 "id": 50393,
 "title": "Kung Fu Panda Holiday",
 "poster": "https://image.tmdb.org/t/p/w1280/gp18R42TbSUlw9VnXFqyecm52lq.jpg",
 "overview": "The Winter Feast is Po's favorite holiday. Every year he and his father hang decorations, cook together, and serve noodle soup to the villagers. But this year Shifu informs Po that as Dragon Warrior, it is his duty to host the formal Winter Feast at the Jade Palace. Po is caught between his obligations as the Dragon Warrior and his family traditions: between Shifu and Mr. Ping.",
 "release_date": 1290729600,
 "_formatted": {
 "id": 50393,
 "title": "Kung Fu Panda Holiday",
 "poster": "https://image.tmdb.org/t/p/w1280/gp18R42TbSUlw9VnXFqyecm52lq.jpg",
 "overview": "The <span class=\"highlight\">Winter Feast</span> is Po's favorite holiday. Every year he and his father hang decorations, cook together, and serve noodle soup to the villagers. But this year Shifu informs Po that as Dragon Warrior, it is his duty to host the formal <span class=\"highlight\">Winter Feast</span> at the Jade Palace. Po is caught between his obligations as the Dragon Warrior and his family traditions: between Shifu and Mr. Ping.",
 "release_date": 1290729600
 }
}
```

Though it is not necessary to use `highlightPreTag` and `highlightPostTag` in conjunction, be careful to ensure tags are correctly matched. In the above example, not setting `highlightPostTag` would result in malformed HTML: `<span>Winter Feast</em>`.

### Show matches position

**Parameter**: `showMatchesPosition`<br />
**Expected value**: `true` or `false`<br />
**Default value**: `false`

Adds a `_matchesPosition` object to the search response that contains the location of each occurrence of queried terms across all fields. This is useful when you need more control than offered by our [built-in highlighting](#attributes-to-highlight). `showMatchesPosition` only works for strings, numbers, and arrays of strings and numbers.

`showMatchesPosition` returns the location of matched query terms within all attributes, even attributes that are not set as [`searchableAttributes`](/learn/relevancy/displayed_searchable_attributes#searchable-fields).

The beginning of a matching term within a field is indicated by `start`, and its length by `length`.

`start` and `length` are measured in bytes and not the number of characters. e.g., `ü` represents two bytes but one character.

#### Example

If you set `showMatchesPosition` to `true` and search for `winter feast`:

You would get the following response with **information about the matches in the `_matchesPosition` object**. Note how Meilisearch searches for `winter` and `feast` separately because of the whitespace:

```json
{
 "id": 50393,
 "title": "Kung Fu Panda Holiday",
 "poster": "https://image.tmdb.org/t/p/w500/rV77WxY35LuYLOuQvBeD1nyWMuI.jpg",
 "overview": "The Winter Feast is Po's favorite holiday. Every year he and his father hang decorations, cook together, and serve noodle soup to the villagers. But this year Shifu informs Po that as Dragon Warrior, it is his duty to host the formal Winter Feast at the Jade Palace. Po is caught between his obligations as the Dragon Warrior and his family traditions: between Shifu and Mr. Ping.",
 "release_date": 1290729600,
 "_matchesPosition": {
 "overview": [
 {
 "start": 4,
 "length": 6
 },
 {
 "start": 11,
 "length": 5
 },
 {
 "start": 234,
 "length": 6
 },
 {
 "start": 241,
 "length": 5
 }
 ]
 }
}
```

### Sort

**Parameter**: `sort`<br />
**Expected value**: A list of attributes written as an array or as a comma-separated string<br />
**Default value**: `null`

Sorts search results at query time according to the specified attributes and indicated order.

Each attribute in the list must be followed by a colon (`:`) and the preferred sorting order: either ascending (`asc`) or descending (`desc`).

Attribute order is meaningful. The first attributes in a list will be given precedence over those that come later.

e.g., `sort="price:asc,author:desc` will prioritize `price` over `author` when sorting results.

When using the POST route, `sort` expects an array of strings.

When using the GET route, `sort` expects the list as a comma-separated string.

[Read more about sorting search results in our dedicated guide.](/learn/filtering_and_sorting/sort_search_results)

#### Example

You can search for science fiction books ordered from cheapest to most expensive:

#### Sorting results with `_geoPoint`

When dealing with documents containing `_geo` data, you can use `_geoPoint` to sort results based on their distance from a specific geographic location.

`_geoPoint` is a sorting function that requires two floating point numbers indicating a location's latitude and longitude. You must also specify whether the sort should be ascending (`asc`) or descending (`desc`):

Queries using `_geoPoint` will always include a `geoDistance` field containing the distance in meters between the document location and the `_geoPoint`:

```json
[
 {
 "id": 1,
 "name": "Nàpiz' Milano",
 "_geo": {
 "lat": 45.4777599,
 "lng": 9.1967508
 },
 "_geoDistance": 1532
 }
]
```

Geographic sorting is only compatible with documents containing `_geo` data. `_geoPoint` ignores all data in the `_geojson` object.

[You can read more about location-based sorting in the dedicated guide.](/learn/filtering_and_sorting/geosearch#sorting-results-with-_geopoint)

### Matching strategy

**Parameter**: `matchingStrategy`<br />
**Expected value**: `last`, `all`, or `frequency`<br />
**Default value**: `last`

Defines the strategy used to match query terms in documents.

#### `last`

`last` returns documents containing all the query terms first. If there are not enough results containing all query terms to meet the requested `limit`, Meilisearch will remove one query term at a time, starting from the end of the query.

With the above code sample, Meilisearch will first return documents that contain all three words. If the results don't meet the requested `limit`, it will also return documents containing only the first two terms, `big fat`, followed by documents containing only `big`.

#### `all`

`all` only returns documents that contain all query terms. Meilisearch will not match any more documents even if there aren't enough to meet the requested `limit`.

The above code sample would only return documents containing all three words.

#### `frequency`

`frequency` returns documents containing all the query terms first. If there are not enough results containing all query terms to meet the requested limit, Meilisearch will remove one query term at a time, starting with the word i.e. the most frequent in the dataset. `frequency` effectively gives more weight to terms that appear less frequently in a set of results.

In a dataset where many documents contain the term `"shirt"`, the above code sample would prioritize documents containing `"white"`.

### Ranking score

**Parameter**: `showRankingScore`<br />
**Expected value**: `true` or `false`<br />
**Default value**: `false`

Adds a global ranking score field, `_rankingScore`, to each document. The `_rankingScore` is a numeric value between `0.0` and `1.0`. The higher the `_rankingScore`, the more relevant the document.

The `sort` ranking rule does not influence the `_rankingScore`. Instead, the document order is determined by the value of the field they are sorted on.

A document's ranking score does not change based on the scores of other documents in the same index.

e.g., if a document A has a score of `0.5` for a query term, this value remains constant no matter the score of documents B, C, or D.

#### Example

The code sample below returns the `_rankingScore` when searching for `dragon` in `movies`:

```json
{
 "hits": [
 {
 "id": 31072,
 "title": "Dragon",
 "overview": "In a desperate attempt to save her kingdom…",
 …
 "_rankingScore": 0.92
 },
 {
 "id": 70057,
 "title": "Dragon",
 "overview": "A sinful martial arts expert wants…",
 …
 "_rankingScore": 0.91
 },
 …
 ],
 …
}
```

### Ranking score details

**Parameter**: `showRankingScoreDetails`<br />
**Expected value**: `true` or `false`<br />
**Default value**: `false`

Adds a detailed global ranking score field, `_rankingScoreDetails`, to each document. `_rankingScoreDetails` is an object containing a nested object for each active ranking rule.

#### Ranking score details object

Each ranking rule details its score in its own object. Fields vary per ranking rule.

##### `words`

- `order`: order in which this ranking rule was applied
- `score`: ranking score for this rule
- `matchingWords`: number of words in the query that match in the document
- `maxMatchingWords`: maximum number of words in the query that can match in the document

##### `typo`

- `order`: order in which this specific ranking rule was applied
- `score`: ranking score for this rule
- `typoCount`: number of typos corrected so that the document matches the query term
- `maxTypoCount`: maximum number of typos accepted

##### `proximity`

- `order`: order in which this ranking rule was applied
- `score`: ranking score for this rule

##### `attribute`

- `order`: order in which this ranking rule was applied
- `score`: ranking score for this rule
- `attributeRankingOrderScore`: score computed from the maximum attribute ranking order for the matching attributes
- `queryWordDistanceScore`: score computed from the distance between the position words in the query and the position of words in matched attributes

##### `exactness`

- `order`: order in which this ranking rule was applied
- `score`: ranking score for this rule
- `matchType`: either `exactMatch`, `matchesStart`, or `noExactMatch`:
 - `exactMatch`: document contains an attribute matching all query terms with no other words between them and in the order they were given
 - `matchesStart`: document contains an attribute with all query terms in the same order as the original query
 - `noExactMatch`: document contains an attribute with at least one query term matching the original query
- `matchingWords`: the number of exact matches in an attribute when `matchType` is `noExactMatch`
- `maxMatchingWords`: the maximum number of exact matches in an attribute when `matchType` is `noExactMatch`

##### `field_name:direction`

The `sort` ranking rule does not appear as a single field in the score details object. Instead, each sorted attribute appears as its own field, followed by a colon (`:`) and the sorting direction: `attribute:direction`.

- `order`: order in which this ranking rule was applied
- `value`: value of the field used for sorting

##### `_geoPoint(lat:lng):direction`

- `order`: order in which this ranking rule was applied
- `value`: value of the field used for sorting
- `distance`: same as [_geoDistance](/learn/filtering_and_sorting/geosearch#finding-the-distance-between-a-document-and-a-_geopoint)

##### `vectorSort(target_vector)`

- `order`: order in which this specific ranking rule was applied
- `value`: vector used for sorting the document
- `similarity`: similarity score between the target vector and the value vector. 1.0 means a perfect similarity, 0.0 a perfect dissimilarity

#### Example

The code sample below returns the `_rankingScoreDetail` when searching for `dragon` in `movies`:

```json
{
 "hits": [
 {
 "id": 31072,
 "title": "Dragon",
 "overview": "In a desperate attempt to save her kingdom…",
 …
 "_rankingScoreDetails": {
 "words": {
 "order": 0,
 "matchingWords": 4,
 "maxMatchingWords": 4,
 "score": 1.0
 },
 "typo": {
 "order": 2,
 "typoCount": 1,
 "maxTypoCount": 4,
 "score": 0.75
 },
 "name:asc": {
 "order": 1,
 "value": "Dragon"
 }
 }
 },
 …
 ],
 …
}
```

### Ranking score threshold

**Parameter**: `rankingScoreThreshold`<br />
**Expected value**: A number between `0.0` and `1.0`<br />
**Default value**: `null`

Excludes results below the specified ranking score. The threshold applies to all search types including full-text search, semantic search, and hybrid search.

Excluded results do not count towards `estimatedTotalHits`, `totalHits`, and facet distribution.

Using `rankingScoreThreshold` with `page` and `hitsPerPage` forces Meilisearch to evaluate the ranking score of all matching documents to return an accurate `totalHits`. This may negatively impact search performance.

Queries with `limit` and `offset` avoid this overhead when using `rankingScoreThreshold`.

#### Example

The following query only returns results with a ranking score bigger than `0.2`:

### Customize attributes to search on at search time

**Parameter**: `attributesToSearchOn`<br />
**Expected value**: A list of searchable attributes written as an array<br />
**Default value**: `["*"]`

Configures a query to only look for terms in the specified attributes.

Instead of a list of attributes, you can pass a wildcard value (`["*"]`) and `null` to `attributesToSearchOn`. In both cases, Meilisearch will search for matches in all searchable attributes.

Attributes passed to `attributesToSearchOn` must also be present in the `searchableAttributes` list.

The order of attributes in `attributesToSearchOn` does not affect relevancy.

#### Example

The following query returns documents whose `overview` includes `"adventure"`:

Results would not include documents containing `"adventure"` in other fields such as `title` or `genre`, even if these fields were present in the `searchableAttributes` list.

### Hybrid search

**Parameter**: `hybrid`<br />
**Expected value**: An object with two fields: `embedder` and `semanticRatio`<br />
**Default value**: `null`

Configures Meilisearch to return search results based on a query's meaning and context.

`hybrid` must be an object. It accepts two fields: `embedder` and `semanticRatio`.

`embedder` must be a string indicating an embedder configured with the `/settings` endpoint. It is mandatory to specify a valid embedder when performing AI-powered searches.

`semanticRatio` must be a number between `0.0` and `1.0` indicating the proportion between keyword and semantic search results. `0.0` causes Meilisearch to only return keyword results. `1.0` causes Meilisearch to only return meaning-based results. Defaults to `0.5`.

#### Example

```json
{
 "query": "PLACEHOLDER_QUERY",
 "processingTimeMs": 10,
 "limit": 20,
 "offset": 0,
 "estimatedTotalHits": 3,
 "semanticHitCount": 3,
 "hits": [
 …
 ]
}
```

### Vector

**Parameter**: `vector`<br />
**Expected value**: an array of numbers<br />
**Default value**: `null`

Use a custom vector to perform a search query. Must be an array of numbers corresponding to the dimensions of the custom vector.

`vector` is mandatory when performing searches with `userProvided` embedders. You may also use `vector` to override an embedder's automatic vector generation.

`vector` dimensions must match the dimensions of the embedder.

If a query does not specify `q`, but contains both `vector` and `hybrid.semanticRatio` bigger than `0`, Meilisearch performs a pure semantic search.

If `q` is missing and `semanticRatio` is explicitly set to `0`, Meilisearch performs a placeholder search without any vector search results.

#### Example

### Display `_vectors` in response

**Parameter**: `retrieveVectors`<br />
**Expected value**: `true` or `false`<br />
**Default value**: `false`

Return document and query embeddings with search results. If `true`, Meilisearch will display vector data in each [document's `_vectors` field](/reference/api/documents#_vectors).

#### Example

```json
{
 "hits": [
 {
 "id": 0,
 "title": "DOCUMENT NAME",
 "_vectors": {
 "default": {
 "embeddings": [0.1, 0.2, 0.3],
 "regenerate": true
 }
 }
 …
 },
 …
 ],
 …
}
```

### Query locales

**Parameter**: `locales`<br />
**Expected value**: array of [supported ISO-639 locales](/reference/api/settings#localized-attributes-object)<br />
**Default value**: `[]`

By default, Meilisearch auto-detects the language of a query. Use this parameter to explicitly state the language of a query.

In case of a mismatch between `locales` and the [localized attributes index setting](/reference/api/settings#localized-attributes), this parameter takes precedence.

`locales` and [`localizedAttributes`](/reference/api/settings#localized-attributes) have the same goal: explicitly state the language used in a search when Meilisearch's language auto-detection is not working as expected.

If you believe Meilisearch is detecting incorrect languages because of the query text, explicitly set the search language with `locales`.

If you believe Meilisearch is detecting incorrect languages because of document, explicitly set the document language at the index level with `localizedAttributes`.

For full control over the way Meilisearch detects languages during indexing and at search time, set both `locales` and `localizedAttributes`.

#### Example

```json
{
 "hits": [
 {
 "id": 0,
 "title": "DOCUMENT NAME",
 "overview_jp": "OVERVIEW TEXT IN JAPANESE"
 }
 …
 ],
 …
}
```

### Media 

**Parameter**: `media`<br />
**Expected value**: Object<br />
**Default value**: `null`

This is an experimental feature. Use the Cloud UI or the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "multimodal": true
 }'
```

Specifies data to populate search fragments when performing multimodal searches.

`media` must be an object whose fields must correspond to the data required by one [search fragment](/reference/api/settings#searchfragments). `media` must match a single search fragment. If `media` matches more than one fragment or no search fragments at all, Meilisearch will return an error.

It is mandatory to specify an embedder when using `media`. `media` is incompatible with `vector`.

#### Example

```json
{
 "hits": [
 {
 "id": 0,
 "title": "DOCUMENT NAME",
 …
 }
 …
 ],
 …
}
```

### Search personalization 

**Parameter**: `personalize`<br />
**Expected value**: Object<br />
**Default value**: `null`

This is an experimental feature. Contact Cloud support to enable it for your projects. If self-hosting, relaunch your instance providing a Cohere key to the search personalization instance option.

Adds user context to [personalize search results according to user profile](/learn/personalization/making_personalized_search_queries).

`personalize` must be an object. It must include a single field, `userContext`.`userContext` must be a string describing the user performing the search.

---

## Settings

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'
import { NoticeTag } from '/snippets/notice_tag.mdx'

import CodeSamplesGetDictionary1 from '/snippets/samples/code_samples_get_dictionary_1.mdx';
import CodeSamplesGetDisplayedAttributes1 from '/snippets/samples/code_samples_get_displayed_attributes_1.mdx';
import CodeSamplesGetDistinctAttribute1 from '/snippets/samples/code_samples_get_distinct_attribute_1.mdx';
import CodeSamplesGetEmbedders1 from '/snippets/samples/code_samples_get_embedders_1.mdx';
import CodeSamplesGetFacetSearchSettings1 from '/snippets/samples/code_samples_get_facet_search_settings_1.mdx';
import CodeSamplesGetFacetingSettings1 from '/snippets/samples/code_samples_get_faceting_settings_1.mdx';
import CodeSamplesGetFilterableAttributes1 from '/snippets/samples/code_samples_get_filterable_attributes_1.mdx';
import CodeSamplesGetLocalizedAttributeSettings1 from '/snippets/samples/code_samples_get_localized_attribute_settings_1.mdx';
import CodeSamplesGetNonSeparatorTokens1 from '/snippets/samples/code_samples_get_non_separator_tokens_1.mdx';
import CodeSamplesGetPaginationSettings1 from '/snippets/samples/code_samples_get_pagination_settings_1.mdx';
import CodeSamplesGetPrefixSearchSettings1 from '/snippets/samples/code_samples_get_prefix_search_settings_1.mdx';
import CodeSamplesGetProximityPrecisionSettings1 from '/snippets/samples/code_samples_get_proximity_precision_settings_1.mdx';
import CodeSamplesGetRankingRules1 from '/snippets/samples/code_samples_get_ranking_rules_1.mdx';
import CodeSamplesGetSearchCutoff1 from '/snippets/samples/code_samples_get_search_cutoff_1.mdx';
import CodeSamplesGetSearchableAttributes1 from '/snippets/samples/code_samples_get_searchable_attributes_1.mdx';
import CodeSamplesGetSeparatorTokens1 from '/snippets/samples/code_samples_get_separator_tokens_1.mdx';
import CodeSamplesGetSettings1 from '/snippets/samples/code_samples_get_settings_1.mdx';
import CodeSamplesGetSortableAttributes1 from '/snippets/samples/code_samples_get_sortable_attributes_1.mdx';
import CodeSamplesGetStopWords1 from '/snippets/samples/code_samples_get_stop_words_1.mdx';
import CodeSamplesGetSynonyms1 from '/snippets/samples/code_samples_get_synonyms_1.mdx';
import CodeSamplesGetTypoTolerance1 from '/snippets/samples/code_samples_get_typo_tolerance_1.mdx';
import CodeSamplesResetDictionary1 from '/snippets/samples/code_samples_reset_dictionary_1.mdx';
import CodeSamplesResetDisplayedAttributes1 from '/snippets/samples/code_samples_reset_displayed_attributes_1.mdx';
import CodeSamplesResetDistinctAttribute1 from '/snippets/samples/code_samples_reset_distinct_attribute_1.mdx';
import CodeSamplesResetEmbedders1 from '/snippets/samples/code_samples_reset_embedders_1.mdx';
import CodeSamplesResetFacetSearchSettings1 from '/snippets/samples/code_samples_reset_facet_search_settings_1.mdx';
import CodeSamplesResetFacetingSettings1 from '/snippets/samples/code_samples_reset_faceting_settings_1.mdx';
import CodeSamplesResetFilterableAttributes1 from '/snippets/samples/code_samples_reset_filterable_attributes_1.mdx';
import CodeSamplesResetLocalizedAttributeSettings1 from '/snippets/samples/code_samples_reset_localized_attribute_settings_1.mdx';
import CodeSamplesResetPaginationSettings1 from '/snippets/samples/code_samples_reset_pagination_settings_1.mdx';
import CodeSamplesResetProximityPrecisionSettings1 from '/snippets/samples/code_samples_reset_proximity_precision_settings_1.mdx';
import CodeSamplesResetRankingRules1 from '/snippets/samples/code_samples_reset_ranking_rules_1.mdx';
import CodeSamplesResetSearchCutoff1 from '/snippets/samples/code_samples_reset_search_cutoff_1.mdx';
import CodeSamplesResetSearchableAttributes1 from '/snippets/samples/code_samples_reset_searchable_attributes_1.mdx';
import CodeSamplesResetSeparatorTokens1 from '/snippets/samples/code_samples_reset_separator_tokens_1.mdx';
import CodeSamplesResetSettings1 from '/snippets/samples/code_samples_reset_settings_1.mdx';
import CodeSamplesResetSortableAttributes1 from '/snippets/samples/code_samples_reset_sortable_attributes_1.mdx';
import CodeSamplesResetStopWords1 from '/snippets/samples/code_samples_reset_stop_words_1.mdx';
import CodeSamplesResetSynonyms1 from '/snippets/samples/code_samples_reset_synonyms_1.mdx';
import CodeSamplesResetTypoTolerance1 from '/snippets/samples/code_samples_reset_typo_tolerance_1.mdx';
import CodeSamplesUpdateDictionary1 from '/snippets/samples/code_samples_update_dictionary_1.mdx';
import CodeSamplesUpdateDisplayedAttributes1 from '/snippets/samples/code_samples_update_displayed_attributes_1.mdx';
import CodeSamplesUpdateDistinctAttribute1 from '/snippets/samples/code_samples_update_distinct_attribute_1.mdx';
import CodeSamplesUpdateEmbedders1 from '/snippets/samples/code_samples_update_embedders_1.mdx';
import CodeSamplesUpdateFacetSearchSettings1 from '/snippets/samples/code_samples_update_facet_search_settings_1.mdx';
import CodeSamplesUpdateFacetingSettings1 from '/snippets/samples/code_samples_update_faceting_settings_1.mdx';
import CodeSamplesUpdateFilterableAttributes1 from '/snippets/samples/code_samples_update_filterable_attributes_1.mdx';
import CodeSamplesUpdateLocalizedAttributeSettings1 from '/snippets/samples/code_samples_update_localized_attribute_settings_1.mdx';
import CodeSamplesUpdateNonSeparatorTokens1 from '/snippets/samples/code_samples_update_non_separator_tokens_1.mdx';
import CodeSamplesUpdatePaginationSettings1 from '/snippets/samples/code_samples_update_pagination_settings_1.mdx';
import CodeSamplesUpdatePrefixSearchSettings1 from '/snippets/samples/code_samples_update_prefix_search_settings_1.mdx';
import CodeSamplesUpdateProximityPrecisionSettings1 from '/snippets/samples/code_samples_update_proximity_precision_settings_1.mdx';
import CodeSamplesUpdateRankingRules1 from '/snippets/samples/code_samples_update_ranking_rules_1.mdx';
import CodeSamplesUpdateSearchCutoff1 from '/snippets/samples/code_samples_update_search_cutoff_1.mdx';
import CodeSamplesUpdateSearchableAttributes1 from '/snippets/samples/code_samples_update_searchable_attributes_1.mdx';
import CodeSamplesUpdateSeparatorTokens1 from '/snippets/samples/code_samples_update_separator_tokens_1.mdx';
import CodeSamplesUpdateSettings1 from '/snippets/samples/code_samples_update_settings_1.mdx';
import CodeSamplesUpdateSortableAttributes1 from '/snippets/samples/code_samples_update_sortable_attributes_1.mdx';
import CodeSamplesUpdateStopWords1 from '/snippets/samples/code_samples_update_stop_words_1.mdx';
import CodeSamplesUpdateSynonyms1 from '/snippets/samples/code_samples_update_synonyms_1.mdx';
import CodeSamplesUpdateTypoTolerance1 from '/snippets/samples/code_samples_update_typo_tolerance_1.mdx';
import CodeSamplesGetVectorStore1 from '/snippets/samples/code_samples_get_vector_store_1.mdx';
import CodeSamplesUpdateVectorStore1 from '/snippets/samples/code_samples_update_vector_store_1.mdx';
import CodeSamplesResetVectorStore1 from '/snippets/samples/code_samples_reset_vector_store_1.mdx';

Use the `/settings` route to customize search settings for a given index. You can either modify all index settings at once using the [update settings endpoint](#update-settings), or use a child route to configure a single setting.

For a conceptual overview of index settings, refer to the [indexes explanation](/learn/getting_started/indexes#index-settings). To learn more about the basics of index configuration, refer to the [index configuration tutorial](/learn/configuration/configuring_index_settings_api).

## Settings interface

[Cloud](https://meilisearch.com/cloud) offers a [user-friendly graphical interface for managing index settings](/learn/configuration/configuring_index_settings) in addition to the `/settings` route. The Cloud interface offers more immediate and visible feedback, and is helpful for tweaking relevancy when used in conjunction with the [search preview](/learn/getting_started/search_preview).

## Settings object

By default, the settings object looks like this. All fields are modifiable.

```json
{
 "displayedAttributes": [
 "*"
 ],
 "searchableAttributes": [
 "*"
 ],
 "filterableAttributes": [],
 "sortableAttributes": [],
 "rankingRules":
 [
 "words",
 "typo",
 "proximity",
 "attribute",
 "sort",
 "exactness"
 ],
 "stopWords": [],
 "nonSeparatorTokens": [],
 "separatorTokens": [],
 "dictionary": [],
 "synonyms": {},
 "distinctAttribute": null,
 "typoTolerance": {
 "enabled": true,
 "minWordSizeForTypos": {
 "oneTypo": 5,
 "twoTypos": 9
 },
 "disableOnWords": [],
 "disableOnAttributes": []
 },
 "faceting": {
 "maxValuesPerFacet": 100
 },
 "pagination": {
 "maxTotalHits": 1000
 },
 "proximityPrecision": "byWord",
 "facetSearch": true,
 "prefixSearch": "indexingTime",
 "searchCutoffMs": null,
 "embedders": {},
 "chat": {},
 "vectorStore": "stable"
}
```

## All settings

This route allows you to retrieve, configure, or reset all of an index's settings at once.

### Get settings

Get the settings of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
{
 "displayedAttributes": [
 "*"
 ],
 "searchableAttributes": [
 "*"
 ],
 "filterableAttributes": [],
 "sortableAttributes": [],
 "rankingRules":
 [
 "words",
 "typo",
 "proximity",
 "attribute",
 "sort",
 "exactness"
 ],
 "stopWords": [],
 "nonSeparatorTokens": [],
 "separatorTokens": [],
 "dictionary": [],
 "synonyms": {},
 "distinctAttribute": null,
 "typoTolerance": {
 "enabled": true,
 "minWordSizeForTypos": {
 "oneTypo": 5,
 "twoTypos": 9
 },
 "disableOnWords": [],
 "disableOnAttributes": []
 },
 "faceting": {
 "maxValuesPerFacet": 100
 },
 "pagination": {
 "maxTotalHits": 1000
 },
 "proximityPrecision": "byWord",
 "facetSearch": true,
 "prefixSearch": "indexingTime",
 "searchCutoffMs": null,
 "embedders": {},
 "chat": {},
 "vectorStore": "stable"
}
```

### Update settings

Update the settings of an index.

Passing `null` to an index setting will reset it to its default value.

Updates in the settings route are **partial**. This means that any parameters not provided in the body will be left unchanged.

If the provided index does not exist, it will be created.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **[`dictionary`](#dictionary)** | Array of strings | Empty | List of strings Meilisearch should parse as a single term | | **[`displayedAttributes`](#displayed-attributes)** | Array of strings | All attributes: `["*"]` | Fields displayed in the returned documents | | **[`distinctAttribute`](#distinct-attribute)** | String | `null` | Search returns documents with distinct (different) values of the given field | | **[`faceting`](#faceting)** | Object | [Default object](#faceting-object) | Faceting settings | | **[`filterableAttributes`](#filterable-attributes)** | Array of strings or objects | Empty | Attributes to use as filters and facets | | **[`pagination`](#pagination)** | Object | [Default object](#pagination-object) | Pagination settings | | **[`proximityPrecision`](#proximity-precision)** | String | `"byWord"` | Precision level when calculating the proximity ranking rule | | **[`facetSearch`](#facet-search)** | Boolean | `true` | Enable or disable [facet search](/reference/api/facet_search) functionality | | **[`prefixSearch`](#prefix-search)** | String | `"indexingTime"` | When Meilisearch should return results only matching the beginning of query | | **[`rankingRules`](#ranking-rules)** | Array of strings | `["words",`<br />`"typo",`<br />`"proximity",`<br />`"attribute",`<br />`"sort",`<br />`"exactness"]` | List of ranking rules in order of importance | | **[`searchableAttributes`](#searchable-attributes)** | Array of strings | All attributes: `["*"]` | Fields in which to search for matching query words sorted by order of importance | | **[`searchCutoffMs`](#search-cutoff)** | Integer | `null`, or 1500ms | Maximum duration of a search query | | **[`separatorTokens`](#separator-tokens)** | Array of strings | Empty | List of characters delimiting where one term begins and ends | | **[`nonSeparatorTokens`](#non-separator-tokens)** | Array of strings | Empty | List of characters not delimiting where one term begins and ends | | **[`sortableAttributes`](#sortable-attributes)** | Array of strings | Empty | Attributes to use when sorting search results | | **[`stopWords`](#stop-words)** | Array of strings | Empty | List of words ignored by Meilisearch when present in search queries | | **[`synonyms`](#synonyms)** | Object | Empty | List of associated words treated similarly | | **[`typoTolerance`](#typo-tolerance)** | Object | [Default object](#typo-tolerance-object) | Typo tolerance settings | | **[`embedders`](#embedders)** | Object of objects | [Default object](#embedders-object) | Embedder required for performing meaning-based search queries | | **[`chat`](#conversation)** | Object | [Default object](#chat-object) | Chat settings for performing conversation-based queries | | **[`vector-store`](#vector-store)** | String | `"stable"` | Vector store used for AI-powered search | #### Example

If Meilisearch encounters an error when updating any of the settings in a request, it immediately stops processing the request and returns an error message. In this case, the database settings remain unchanged. The returned error message will only address the first error encountered.

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset settings

Reset all the settings of an index to their [default value](#settings-object).

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Dictionary

Allows users to instruct Meilisearch to consider groups of strings as a single term by adding a supplementary dictionary of user-defined terms.

This is particularly useful when working with datasets containing many domain-specific words, and in languages where words are not separated by whitespace such as Japanese.

Custom dictionaries are also useful in a few use-cases for space-separated languages, such as datasets with names such as `"J. R. R. Tolkien"` and `"W. E. B. Du Bois"`.

User-defined dictionaries can be used together with synonyms. It can be useful to configure Meilisearch so different spellings of an author's initials return the same results:

```json
"dictionary": ["W. E. B.", "W.E.B."],
"synonyms": {
 "W. E. B.": ["W.E.B."],
 "W.E.B.": ["W. E. B."]
}
```

### Get dictionary

Get an index's user-defined dictionary.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
[]
```

### Update dictionary

Update an index's user-defined dictionary.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```json
["J. R. R.", "W. E. B."]
```

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2023-09-11T15:39:06.073314Z"
}
```

Use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset dictionary

Reset an index's dictionary to its default value, `[]`.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2022-04-14T20:53:32.863107Z"
}
```

Use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Displayed attributes

The attributes added to the `displayedAttributes` list appear in search results. `displayedAttributes` only affects the search endpoints. It has no impact on the [get documents with POST](/reference/api/documents#get-documents-with-post) and [get documents with GET](/reference/api/documents#get-documents-with-get) endpoints.

By default, the `displayedAttributes` array is equal to all fields in your dataset. This behavior is represented by the value `["*"]`.

[To learn more about displayed attributes, refer to our dedicated guide.](/learn/relevancy/displayed_searchable_attributes#displayed-fields)

### Get displayed attributes

Get the displayed attributes of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
[
 "title",
 "overview",
 "genres",
 "release_date.year"
]
```

### Update displayed attributes

Update the displayed attributes of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
[, , …]
```

An array of strings. Each string should be an attribute that exists in the selected index.

If an attribute contains an object, you can use dot notation to specify one or more of its keys, e.g., `"displayedAttributes": ["release_date.year"]`.

If the field does not exist, no error will be thrown.

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset displayed attributes

Reset the displayed attributes of the index to the default value.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Distinct attribute

The distinct attribute is a field whose value will always be unique in the returned documents.

Updating distinct attributes will re-index all documents in the index, which can take some time. We recommend updating your index settings first and then adding documents as this reduces RAM consumption.

[To learn more about the distinct attribute, refer to our dedicated guide.](/learn/relevancy/distinct_attribute)

### Get distinct attribute

Get the distinct attribute of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
"skuid"
```

### Update distinct attribute

Update the distinct attribute field of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```

```

A string. The string should be an attribute that exists in the selected index.

If an attribute contains an object, you can use dot notation to set one or more of its keys as a value for this setting, e.g., `"distinctAttribute": "product.skuid"`.

If the field does not exist, no error will be thrown.

[To learn more about the distinct attribute, refer to our dedicated guide.](/learn/relevancy/distinct_attribute)

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset distinct attribute

Reset the distinct attribute of an index to its default value.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Faceting

With Meilisearch, you can create [faceted search interfaces](/learn/filtering_and_sorting/search_with_facet_filters). This setting allows you to:

- Define the maximum number of values returned by the `facets` search parameter
- Sort facet values by value count or alphanumeric order

[To learn more about faceting, refer to our dedicated guide.](/learn/filtering_and_sorting/search_with_facet_filters)

### Faceting object | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`maxValuesPerFacet`** | Integer | `100` | Maximum number of facet values returned for each facet. Values are sorted in ascending lexicographical order | | **`sortFacetValuesBy`** | Object | All facet values are sorted in ascending alphanumeric order (`"*": "alpha"`) | Customize facet order to sort by descending value count (`count`) or ascending alphanumeric order (`alpha`) | ### Get faceting settings

Get the faceting settings of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
{
 "maxValuesPerFacet": 100,
 "sortFacetValuesBy": {
 "*": "alpha"
 }
}
```

### Update faceting settings

Partially update the faceting settings for an index. Any parameters not provided in the body will be left unchanged.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
{
 "maxValuesPerFacet": ,
 "sortFacetValuesBy": {
 : "count",
 : "alpha"
 }
}
``` | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`maxValuesPerFacet`** | Integer | `100` | Maximum number of facet values returned for each facet. Values are sorted in ascending lexicographical order | | **`sortFacetValuesBy`** | Object | All facet values are sorted in ascending alphanumeric order (`"*": "alpha"`) | Customize facet order to sort by descending value count(`count`) or ascending alphanumeric order (`alpha`) | Suppose a query's search results contain a total of three values for a `colors` facet: `blue`, `green`, and `red`. If you set `maxValuesPerFacet` to `2`, Meilisearch will only return `blue` and `green` in the response body's `facetDistribution` object.

Setting `maxValuesPerFacet` to a high value might negatively impact performance.

#### Example

The following code sample sets `maxValuesPerFacet` to `2`, sorts the `genres` facet by descending count, and all other facets in ascending alphanumeric order:

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2022-04-14T20:56:44.991039Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset faceting settings

Reset an index's faceting settings to their [default value](#faceting-object). Setting `sortFacetValuesBy` to `null`(`--data-binary '{ "sortFacetValuesBy": null }'`), will restore it to the default value (`"*": "alpha"`).

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2022-04-14T20:53:32.863107Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Filterable attributes

Attributes in the `filterableAttributes` list can be used as [filters](/learn/filtering_and_sorting/filter_search_results) or [facets](/learn/filtering_and_sorting/search_with_facet_filters).

Updating filterable attributes will re-index all documents in the index, which can take some time. To reduce RAM consumption, first update your index settings and then add documents.

### Filterable attribute object

`filterableAttributes` may be an array of either strings or filterable attribute objects.

Filterable attribute objects must contain the following fields: | Name | Type | Default value | Description | | --- | --- | --- | --- | | **`attributePatterns`** | Array of strings | `[]` | A list of strings indicating filterable fields | | **`features`** | Object | `{"facetSearch": false, "filter": {"equality": true, "comparison": false}` | A list outlining filter types enabled for the specified attributes | #### `attributePatterns`

Attribute patterns may begin or end with a * wildcard to match multiple fields: `customer_*`, `attribute*`.

#### `features`

`features` allows you to decide which filter features are allowed for the specified attributes. It accepts the following fields:

- `facetSearch`: Whether facet search should be enabled for the specified attributes. Boolean, defaults to `false`
- `filter`: A list outlining the filter types for the specified attributes. Must be an object and accepts the following fields:
 - `equality`: Enables `=`, `!=`, `IN`, `EXISTS`, `IS NULL`, `IS EMPTY`, `NOT`, `AND`, and `OR`. Boolean, defaults to `true`
 - `comparison`: Enables `>`, `>=`, `<`, `<=`, `TO`, `EXISTS`, `IS NULL`, `IS EMPTY`, `NOT`, `AND`, and `OR`. Boolean, defaults to `false`

Calculating `comparison` filters is a resource-intensive operation. Disabling them may lead to better search and indexing performance. `equality` filters use fewer resources and have limited impact on performance.

#### Filterable attributes and reserved attributes

Use the simple string syntax to match reserved attributes. Reserved Meilisearch fields are always prefixed with an underscore (`_`), such as `_geo` and `_vector`.

If set as a filterable attribute, reserved attributes ignore the `features` field and automatically activate all search features. Reserved fields will not be matched by wildcard `attributePatterns` such as `_*`.

### Get filterable attributes

Get the filterable attributes for an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
[
 "genres",
 "director",
 "release_date.year"
]
```

### Update filterable attributes

Update an index's filterable attributes list.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
[, , …]
```

An array of strings containing the attributes that can be used as filters at query time. All filter types are enabled for the specified attributes when using the array of strings format.

You may also use an array of objects:

```
[
 {
 "attributePatterns": [, , …],
 "features": {
 "facetSearch": ,
 "filter": {
 "equality": ,
 "comparison": 
 }
 }
 }
]
```

If the specified field does not exist, Meilisearch will silently ignore it.

If an attribute contains an object, you can use dot notation to set one or more of its keys as a value for this setting: `"filterableAttributes": ["release_date.year"]` or `"attributePatterns": ["release_date.year"]`.

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset filterable attributes

Reset an index's filterable attributes list back to its default value.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Localized attributes

By default, Meilisearch auto-detects the languages used in your documents. This setting allows you to explicitly define which languages are present in a dataset, and in which fields.

Localized attributes affect `searchableAttributes`, `filterableAttributes`, and `sortableAttributes`.

Configuring multiple languages for a single index may negatively impact performance.

[`locales`](/reference/api/search#query-locales) and `localizedAttributes` have the same goal: explicitly state the language used in a search when Meilisearch's language auto-detection is not working as expected.

If you believe Meilisearch is detecting incorrect languages because of the query text, explicitly set the search language with `locales`.

If you believe Meilisearch is detecting incorrect languages because of document, explicitly set the document language at the index level with `localizedAttributes`.

For full control over the way Meilisearch detects languages during indexing and at search time, set both `locales` and `localizedAttributes`.

### Localized attributes object

`localizedAttributes` must be an array of locale objects. Its default value is `[]`.

Locale objects must have the following fields: | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`locales`** | Array of strings | `[]` | A list of strings indicating one or more ISO-639 locales | | **`attributePatterns`** | Array of strings | `[]` | A list of strings indicating which fields correspond to the specified locales | #### `locales`

Meilisearch supports the following [ISO-639-3](https://iso639-3.sil.org/) three-letter `locales`: `epo`, `eng`, `rus`, `cmn`, `spa`, `por`, `ita`, `ben`, `fra`, `deu`, `ukr`, `kat`, `ara`, `hin`, `jpn`, `heb`, `yid`, `pol`, `amh`, `jav`, `kor`, `nob`, `dan`, `swe`, `fin`, `tur`, `nld`, `hun`, `ces`, `ell`, `bul`, `bel`, `mar`, `kan`, `ron`, `slv`, `hrv`, `srp`, `mkd`, `lit`, `lav`, `est`, `tam`, `vie`, `urd`, `tha`, `guj`, `uzb`, `pan`, `aze`, `ind`, `tel`, `pes`, `mal`, `ori`, `mya`, `nep`, `sin`, `khm`, `tuk`, `aka`, `zul`, `sna`, `afr`, `lat`, `slk`, `cat`, `tgl`, `hye`.

You may alternatively use [ISO-639-1 two-letter equivalents](https://iso639-3.sil.org/code_tables/639/data) to the supported `locales`.

You may also assign an empty array to `locales`. In this case, Meilisearch will auto-detect the language of the associated `attributePatterns`.

#### `attributePatterns`

Attribute patterns may begin or end with a `*` wildcard to match multiple fields: `en_*`, `*-ar`.

You may also set `attributePatterns` to `*`, in which case Meilisearch will treat all fields as if they were in the associated locale.

### Get localized attributes settings

Get the localized attributes settings of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
[
 {"locales": ["jpn"], "attributePatterns": ["*_ja"]}
]
```

### Update localized attribute settings

Update the localized attributes settings of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
[
 {
 "locales": [, …],
 "attributePatterns": [, …],
 }
]
``` | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`localizedAttributes`** | Array of objects | `[]` | Explicitly set specific locales for one or more attributes | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_NAME",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2022-04-14T20:56:44.991039Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset localized attributes settings

Reset an index's localized attributes to their [default value](#localized-attributes-object).

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_NAME",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2022-04-14T20:53:32.863107Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Pagination

To protect your database from malicious scraping, Meilisearch has a default limit of 1000 results per search. This setting allows you to configure the maximum number of results returned per search.

`maxTotalHits` takes priority over search parameters such as `limit`, `offset`, `hitsPerPage`, and `page`.

e.g., if you set `maxTotalHits` to 100, you will not be able to access search results beyond 100 no matter the value configured for `offset`.

[To learn more about paginating search results with Meilisearch, refer to our dedicated guide.](/guides/front_end/pagination)

### Pagination object | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`maxTotalHits`** | Integer | `1000` | The maximum number of search results Meilisearch can return | Setting `maxTotalHits` to a value higher than the default will negatively impact search performance. Setting `maxTotalHits` to values over `20000` may result in queries taking seconds to complete.

### Get pagination settings

Get the pagination settings of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
{
 "maxTotalHits": 1000
}
```

### Update pagination settings

Partially update the pagination settings for an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
{maxTotalHits: }
``` | Name | Type | Default value | Description | | :--- | :--- | :--- | :--- | | **`maxTotalHits`** | Integer | `1000` | The maximum number of search results Meilisearch can return | Setting `maxTotalHits` to a value higher than the default will negatively impact search performance. Setting `maxTotalHits` to values over `20000` may result in queries taking seconds to complete.

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2022-04-14T20:56:44.991039Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset pagination settings

Reset an index's pagination settings to their [default value](#pagination-object).

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2022-04-14T20:53:32.863107Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Proximity precision

Calculating the distance between words is a resource-intensive operation. Lowering the precision of this operation may significantly improve performance and will have little impact on result relevancy in most use-cases. Meilisearch uses word distance when [ranking results according to proximity](/learn/relevancy/ranking_rules#3-proximity) and when users perform [phrase searches](/reference/api/search#phrase-search).

`proximityPrecision` accepts one of the following string values:

- `"byWord"`: calculate the precise distance between query terms. Higher precision, but may lead to longer indexing time. This is the default setting
- `"byAttribute"`: determine if multiple query terms are present in the same attribute. Lower precision, but shorter indexing time

### Get proximity precision settings

Get the proximity precision settings of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```
"byWord"
```

### Update proximity precision settings

Update the pagination settings for an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
"byWord"|"byAttribute"
```

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2023-04-14T15:50:29.821044Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset proximity precision settings

Reset an index's proximity precision setting to its default value.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2023-04-14T15:51:47.821044Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Facet search

Processing filterable attributes for facet search is a resource-intensive operation. This feature is enabled by default, but disabling it may speed up indexing.

`facetSearch` accepts a single Boolean value. If set to `false`, it disables facet search for the whole index. Meilisearch returns an error if you try to access the `/facet-search` endpoint when facet search is disabled.

### Get facet search settings

Get the facet search settings of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
true
```

### Update facet search settings

Update the facet search settings for an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```

```

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_UID",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2024-07-19T22:33:18.523881Z"
}
```

Use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset facet search settings

Reset an index's facet search to its default settings.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_UID",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2024-07-19T22:35:33.723983Z"
}
```

Use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Prefix search

Prefix search is the process through which Meilisearch matches documents that begin with a specific query term, instead of only exact matches. This is a resource-intensive operation that happens during indexing by default.

Use `prefixSearch` to change how prefix search works. It accepts one of the following strings:

- `"indexingTime"`: calculate prefix search during indexing. This is the default behavior
- `"disabled"`: do not calculate prefix search. May speed up indexing, but will severely impact search result relevancy

### Get prefix search settings

Get the prefix search settings of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
"indexingTime"
```

### Update prefix search settings

Update the prefix search settings for an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
"indexingTime" | "disabled"
```

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_UID",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2024-07-19T22:33:18.523881Z"
}
```

Use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset prefix search settings

Reset an index's prefix search to its default settings.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_UID",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2024-07-19T22:35:33.723983Z"
}
```

Use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Ranking rules

Ranking rules are built-in rules that rank search results according to certain criteria. They are applied in the same order in which they appear in the `rankingRules` array.

[To learn more about ranking rules, refer to our dedicated guide.](/learn/relevancy/relevancy)

### Ranking rules array | Name | Description | | :--- | :--- | | **`"words"`** | Sorts results by decreasing number of matched query terms | | **`"typo"`** | Sorts results by increasing number of typos | | **`"proximity"`** | Sorts results by increasing distance between matched query terms | | **`"attribute"`** | Sorts results based on the attribute ranking order | | **`"sort"`** | Sorts results based on parameters decided at query time | | **`"exactness"`** | Sorts results based on the similarity of the matched words with the query words | #### Default order

```json
[
 "words",
 "typo",
 "proximity",
 "attribute",
 "sort",
 "exactness"
]
```

### Get ranking rules

Get the ranking rules of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
[
 "words",
 "typo",
 "proximity",
 "attribute",
 "sort",
 "exactness",
 "release_date:desc"
]
```

### Update ranking rules

Update the ranking rules of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
[, , …]
```

An array that contains ranking rules in order of importance.

To create a custom ranking rule, give an attribute followed by a colon (`:`) and either `asc` for ascending order or `desc` for descending order.

- To apply an **ascending sort** (results sorted by increasing value): `attribute_name:asc`
- To apply a **descending sort** (results sorted by decreasing value): `attribute_name:desc`

If some documents do not contain the attribute defined in a custom ranking rule, the application of the ranking rule is undefined and the search results might not be sorted as you expected.

Make sure that any attribute used in a custom ranking rule is present in all of your documents. e.g., if you set the custom ranking rule `desc(year)`, make sure that all your documents contain the attribute `year`.

[To learn more about ranking rules, refer to our dedicated guide.](/learn/relevancy/ranking_rules)

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset ranking rules

Reset the ranking rules of an index to their [default value](#default-order).

Resetting ranking rules is not the same as removing them. To remove a ranking rule, use the [update ranking rules endpoint](#update-ranking-rules).

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Searchable attributes

The values associated with attributes in the `searchableAttributes` list are searched for matching query words. The order of the list also determines the [attribute ranking order](/learn/relevancy/attribute_ranking_order).

By default, the `searchableAttributes` array is equal to all fields in your dataset. This behavior is represented by the value `["*"]`.

Updating searchable attributes will re-index all documents in the index, which can take some time. We recommend updating your index settings first and then adding documents as this reduces RAM consumption.

[To learn more about searchable attributes, refer to our dedicated guide.](/learn/relevancy/displayed_searchable_attributes#searchable-fields)

### Get searchable attributes

Get the searchable attributes of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
[
 "title",
 "overview",
 "genres",
 "release_date.year"
]
```

### Update searchable attributes

Update the searchable attributes of an index.

Due to an implementation bug, manually updating `searchableAttributes` will change the displayed order of document fields in the JSON response. This behavior is inconsistent and will be fixed in a future release.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
[, , …]
```

An array of strings. Each string should be an attribute that exists in the selected index. The array should be given in [order of importance](/learn/relevancy/attribute_ranking_order): from the most important attribute to the least important attribute.

If an attribute contains an object, you can use dot notation to set one or more of its keys as a value for this setting: `"searchableAttributes": ["release_date.year"]`.

If the field does not exist, no error will be thrown.

[To learn more about searchable attributes, refer to our dedicated guide.](/learn/relevancy/displayed_searchable_attributes#searchable-fields)

#### Example

In this example, a document with a match in `title` will be more relevant than another document with a match in `overview`.

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset searchable attributes

Reset the searchable attributes of the index to the default value.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Search cutoff

Configure the maximum duration of a search query. If a search operation reaches the cutoff, Meilisearch immediately interrupts it and returns all computed results.

By default, Meilisearch interrupts searches after 1500 milliseconds.

### Get search cutoff

Get an index's search cutoff value.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
null
```

### Update search cutoff

Update an index's search cutoff value.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
150
```

A single integer indicating the cutoff value in milliseconds.

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2023-03-21T06:33:41.000000Z"
}
```

Use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset search cutoff

Reset an index's search cutoff value to its default value, `null`. This translates to a cutoff of 1500ms.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2023-03-21T07:05:16.000000Z"
}
```

## Separator tokens

Configure strings as custom separator tokens indicating where a word ends and begins.

Tokens in the `separatorTokens` list are added on top of [Meilisearch's default list of separators](/learn/engine/datatypes#string). To remove separators from the default list, use [the `nonSeparatorTokens` setting](#non-separator-tokens).

### Get separator tokens

Get an index's list of custom separator tokens.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
[]
```

### Update separator tokens

Update an index's list of custom separator tokens.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
["|", "&hellip;"]
```

An array of strings, with each string indicating a word separator.

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

Use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset separator tokens

Reset an index's list of custom separator tokens to its default value, `[]`.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

Use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Non-separator tokens

Remove tokens from Meilisearch's default [list of word separators](/learn/engine/datatypes#string).

### Get non-separator tokens

Get an index's list of non-separator tokens.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
[]
```

### Update non-separator tokens

Update an index's list of non-separator tokens.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
["@", "#"]
```

An array of strings, with each string indicating a token present in [list of word separators](/learn/engine/datatypes#string).

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

Use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset non-separator tokens

Reset an index's list of non-separator tokens to its default value, `[]`.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

Use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Sortable attributes

Attributes that can be used when sorting search results using the [`sort` search parameter](/reference/api/search#sort).

Updating sortable attributes will re-index all documents in the index, which can take some time. We recommend updating your index settings first and then adding documents as this reduces RAM consumption.

[To learn more about sortable attributes, refer to our dedicated guide.](/learn/filtering_and_sorting/sort_search_results)

### Get sortable attributes

Get the sortable attributes of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
[
 "price",
 "author.surname"
]
```

### Update sortable attributes

Update an index's sortable attributes list.

[You can read more about sorting at query time on our dedicated guide.](/learn/filtering_and_sorting/sort_search_results)

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
[, , …]
```

An array of strings. Each string should be an attribute that exists in the selected index.

If an attribute contains an object, you can use dot notation to set one or more of its keys as a value for this setting: `"sortableAttributes": ["author.surname"]`.

If the field does not exist, no error will be thrown.

[To learn more about sortable attributes, refer to our dedicated guide.](/learn/filtering_and_sorting/sort_search_results)

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset sortable attributes

Reset an index's sortable attributes list back to its default value.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Stop words

Words added to the `stopWords` list are ignored in future search queries.

Updating stop words will re-index all documents in the index, which can take some time. We recommend updating your index settings first and then adding documents as this reduces RAM consumption.

Stop words are strongly related to the language used in your dataset. e.g., most datasets containing English documents will have countless occurrences of `the` and `of`. Italian datasets, instead, will benefit from ignoring words like `a`, `la`, or `il`.

[This open-source project on GitHub](https://github.com/stopwords-iso/stopwords-iso) offers lists of possible stop words in different languages. Note that, depending on your dataset and use case, you will need to tweak these lists for optimal results.

### Get stop words

Get the stop words list of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 Ok`

```json
[
 "of",
 "the",
 "to"
]
```

### Update stop words

Update the list of stop words of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
[, , …]
```

An array of strings. Each string should be a single word.

If a list of stop words already exists, it will be overwritten (_replaced_).

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset stop words

Reset the list of stop words of an index to its default value.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Synonyms

The `synonyms` object contains words and their respective synonyms. A synonym in Meilisearch is considered equal to its associated word for the purposes of calculating search results.

[To learn more about synonyms, refer to our dedicated guide.](/learn/relevancy/synonyms)

### Get synonyms

Get the list of synonyms of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
{
 "wolverine": [
 "xmen",
 "logan"
 ],
 "logan": [
 "wolverine",
 "xmen"
 ],
 "wow": [
 "world of warcraft"
 ]
}
```

### Update synonyms

Update the list of synonyms of an index. Synonyms are [normalized](/learn/relevancy/synonyms#normalization).

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
{
 : [, , …],
 …
}
```

An object that contains all synonyms and their associated words. Add the associated words in an array to set a synonym for a word.

[To learn more about synonyms, refer to our dedicated guide.](/learn/relevancy/synonyms)

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset synonyms

Reset the list of synonyms of an index to its default value.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Typo tolerance

Typo tolerance helps users find relevant results even when their search queries contain spelling mistakes or typos. This setting allows you to configure the minimum word size for typos and disable typo tolerance for specific words or attributes.

[To learn more about typo tolerance, refer to our dedicated guide.](/learn/relevancy/typo_tolerance_settings)

### Typo tolerance object | Name | Type | Default Value | Description | | :--- | :--- | :--- | :--- | | **`enabled`** | Boolean | `true` | Whether typo tolerance is enabled or not | | **`minWordSizeForTypos.oneTypo`** | Integer | `5` | The minimum word size for accepting 1 typo; must be between `0` and `twoTypos` | | **`minWordSizeForTypos.twoTypos`** | Integer | `9` | The minimum word size for accepting 2 typos; must be between `oneTypo` and `255` | | **`disableOnWords`** | Array of strings | Empty | An array of words for which the typo tolerance feature is disabled | | **`disableOnAttributes`** | Array of strings | Empty | An array of attributes for which the typo tolerance feature is disabled | | **`disableOnNumbers`** | Boolean | `false` | Whether typo tolerance for numbers is disabled or enabled | ### Get typo tolerance settings

Get the typo tolerance settings of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
{
 "enabled": true,
 "minWordSizeForTypos": {
 "oneTypo": 5,
 "twoTypos": 9
 },
 "disableOnWords": [],
 "disableOnAttributes": []
}
```

### Update typo tolerance settings

Partially update the typo tolerance settings for an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
{
 "enabled": ,
 "minWordSizeForTypos": {
 "oneTypo": ,
 "twoTypos": 
 },
 "disableOnWords": [, , …],
 "disableOnAttributes": [, , …]
 "disableOnNumbers": ,
}
``` | Name | Type | Default Value | Description | | :--- | :--- | :--- | :--- | | **`enabled`** | Boolean | `true` | Whether typo tolerance is enabled or not | | **`minWordSizeForTypos.oneTypo`** | Integer | `5` | The minimum word size for accepting 1 typo; must be between `0` and `twoTypos` | | **`minWordSizeForTypos.twoTypos`** | Integer | `9` | The minimum word size for accepting 2 typos; must be between `oneTypo` and `255` | | **`disableOnWords`** | Array of strings | Empty | An array of words for which the typo tolerance feature is disabled | | **`disableOnAttributes`** | Array of strings | Empty | An array of attributes for which the typo tolerance feature is disabled | | **`disableOnNumbers`** | Boolean | `false` | Whether typo tolerance for numbers is disabled or enabled | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2022-04-14T20:56:44.991039Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset typo tolerance settings

Reset an index's typo tolerance settings to their [default value](#typo-tolerance-object).

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2022-04-14T20:53:32.863107Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Embedders

Embedders translate documents and queries into vector embeddings. You must configure at least one embedder to use AI-powered search.

### Embedders object

The embedders object may contain up to 256 embedder objects. Each embedder object must be assigned a unique name:

```json
{
 "default": {
 "source": "huggingFace",
 "model": "BAAI/bge-base-en-v1.5",
 "documentTemplate": "A movie titled '{{doc.title}}' whose description starts with {{doc.overview|truncatewords: 20}}"
 },
 "openai": {
 "source": "openAi",
 "apiKey": "OPENAI_API_KEY",
 "model": "text-embedding-3-small",
 "documentTemplate": "A movie titled {{doc.title}} whose description starts with {{doc.overview|truncatewords: 20}}",
 }
}
```

These embedder objects may contain the following fields: | Name | Type | Default Value | Description | | --- | --- | --- | --- | | **`source`** | String | Empty | The third-party tool that will generate embeddings from documents. Must be `openAi`, `huggingFace`, `ollama`, `rest`, or `userProvided` | | **`url`** | String | `http://localhost:11434/api/embeddings` | The URL Meilisearch contacts when querying the embedder | | **`apiKey`** | String | Empty | Authentication token Meilisearch should send with each request to the embedder. If not present, Meilisearch will attempt to read it from environment variables | | **`model`** | String | Empty | The model your embedder uses when generating vectors | | **`documentTemplate`** | String | `{% for field in fields %} {% if field.is_searchable and not field.value == nil %}{{ field.name }}: {{ field.value }} {% endif %} {% endfor %}` | Template defining the data Meilisearch sends to the embedder | | **`documentTemplateMaxBytes`** | Integer | `400` | Maximum allowed size of rendered document template | | **`dimensions`** | Integer | Empty | Number of dimensions in the chosen model. If not supplied, Meilisearch tries to infer this value | | **`revision`** | String | Empty | Model revision hash | | **`distribution`** | Object | Empty | Describes the natural distribution of search results. Must contain two fields, `mean` and `sigma`, each containing a numeric value between `0` and `1` | | **`request`** | Object | Empty | A JSON value representing the request Meilisearch makes to the remote embedder | | **`response`** | Object | Empty | A JSON value representing the response Meilisearch expects from the remote embedder | | **`binaryQuantized`** | Boolean | Empty | Once set to `true`, irreversibly converts all vector dimensions to 1-bit values | | **`indexingEmbedder`** | Object | Empty | Configures embedder to vectorize documents during indexing | | **`searchEmbedder`** | Object | Empty | Configures embedder to vectorize search queries | | **`pooling`** | String | `"useModel"` | Pooling method for Hugging Face embedders | | **`indexingFragments`** | Object | Empty | Configures multimodal embedding generation at indexing time | | **`searchFragments`** | Object | Empty | Configures data handling during multimodal search | ### Get embedder settings

Get the embedders configured for an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
{
 "default": {
 "source": "openAi",
 "apiKey": "OPENAI_API_KEY",
 "model": "text-embedding-3-small",
 "documentTemplate": "A movie titled {{doc.title}} whose description starts with {{doc.overview|truncatewords: 20}}",
 "dimensions": 1536
 }
}
```

### Update embedder settings

Partially update the embedder settings for an index. When this setting is updated Meilisearch may reindex all documents and regenerate their embeddings.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```json
{
 "default": {
 "source": ,
 "url": ,
 "apiKey": ,
 "model": ,
 "documentTemplate": ,
 "documentTemplateMaxBytes": ,
 "dimensions": ,
 "revision": ,
 "distribution": {
 "mean": ,
 "sigma": 
 },
 "request": { … },
 "response": { … },
 "headers": { … },
 "binaryQuantized": ,
 "pooling": ,
 "indexingEmbedder": { … },
 "searchEmbedder": { … }
 }
}
```

Set an embedder to `null` to remove it from the embedders list.

##### `source`

Use `source` to configure an embedder's source. The source corresponds to a service that generates embeddings from your documents.

Meilisearch supports the following sources:

- `openAi`
- `huggingFace`
- `ollama`
- `rest`
- `userProvided`
- `composite` 

`rest` is a generic source compatible with any embeddings provider offering a REST API.

Use `userProvided` when you want to generate embeddings manually. In this case, you must include vector data in your documents' `_vectors` field. You must also generate vectors for search queries.

This field is mandatory.

###### Composite embedders 

Choose `composite` to use one embedder during indexing time, and another embedder at search time. Must be used together with [`indexingEmbedder` and `searchEmbedder`](#indexingembedder-and-searchembedder).

This is an experimental feature. Use the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "compositeEmbedders": true
 }'
```

##### `url`

Meilisearch queries `url` to generate vector embeddings for queries and documents. `url` must point to a REST-compatible embedder. You may also use `url` to work with proxies, such as when targeting `openAi` from behind a proxy.

This field is mandatory when using `rest` embedders.

This field is optional when using `ollama` and `openAi` embedders. `ollama` URLs must end with either `/api/embed` or `/api/embeddings`.

This field is incompatible with `huggingFace` and `userProvided` embedders.

##### `apiKey`

Authentication token Meilisearch should send with each request to the embedder. Meilisearch redacts this value when returning embedder settings. Do not use the redacted API key when updating settings.

This field is mandatory if using a protected `rest` embedder.

This field is optional for `openAI` and `ollama` embedders. If you don't specify `apiKey` when using `openAI`, Meilisearch attempts to read it from the `OPENAI_API_KEY` environment variable.

This field is incompatible with `huggingFace` and `userProvided` embedders.

##### `model`

The model your embedder uses when generating vectors. These are the officially supported models Meilisearch supports:

- `openAi`: `text-embedding-3-small`, `text-embedding-3-large`, `openai-text-embedding-ada-002`
- `huggingFace`: `BAAI/bge-base-en-v1.5`

Other models, such as [HuggingFace's BERT models](https://huggingface.co/models?other=bert) and [ModernBERT](https://huggingface.co/models?other=modernbert), as well as some of the models provided by Ollama and REST embedders, may also be compatible with Meilisearch.

This field is mandatory for `Ollama` embedders.

This field is optional for `openAi` and `huggingFace`. By default, Meilisearch uses `text-embedding-3-small` and `BAAI/bge-base-en-v1.5` respectively.

This field is incompatible with `rest` and `userProvided` embedders.

##### `documentTemplate`

`documentTemplate` is a string containing a [Liquid template](https://shopify.github.io/liquid/basics/introduction). When using an embedding generation service such as OpenAI, Meillisearch interpolates the template for each document and sends the resulting text to the embedder. The embedder then generates document vectors based on this text. If used with a custom embedder, Meilisearch will return an error.

You may use the following context values:

- `{{doc.FIELD}}`: `doc` stands for the document itself. `FIELD` must correspond to an attribute present on all documents value will be replaced by the value of that field in the input document
- `{{fields}}`: a list of all the `field`s appearing in any document in the index. Each `field` object in this list has the following properties:
 - `name`: the field's attribute
 - `value`: the field's value
 - `is_searchable`: whether the field is present in the searchable attributes list

If a `field` does not exist in a document, its `value` is `nil`.

For best results, build short templates that only contain highly relevant data. If working with a long field, consider [truncating it](https://shopify.github.io/liquid/filters/truncatewords/). If you do not manually set it, `documentTemplate` will include all searchable and non-null document fields. This may lead to suboptimal performance and relevancy.

This field is incompatible with `userProvided` embedders.

This field is optional but strongly encouraged for all other embedders.

##### `documentTemplateMaxBytes`

The maximum size of a rendered document template. Longer texts are truncated to fit the configured limit.

`documentTemplateMaxBytes` must be an integer. It defaults to `400`.

This field is incompatible with `userProvided` embedders.

This field is optional for all other embedders.

##### `dimensions`

Number of dimensions in the chosen model. If not supplied, Meilisearch tries to infer this value.

In most cases, `dimensions` should be the exact same value of your chosen model. Setting `dimensions` to a value lower than the model may lead to performance improvements and is only supported in the following OpenAI models:

- `openAi`: `text-embedding-3-small`, `text-embedding-3-large`

This field is mandatory for `userProvided` embedders.

This field is optional for `openAi`, `huggingFace`, `ollama`, and `rest` embedders.

##### `revision`

Use this field to use a specific revision of a model.

This field is optional for the `huggingFace` embedder.

This field is incompatible with all other embedders.

##### `request`

`request` must be a JSON object with the same structure and data of the request you must send to your `rest` embedder.

The field containing the input text Meilisearch should send to the embedder must be replaced with `"{{text}}"`:

```json
{
 "source": "rest",
 "request": {
 "prompt": "{{text}}"
 …
 },
 …
}
```

If sending multiple documents in a single request, replace the input field with `["{{text}}", "{{..}}"]`:

```json
{
 "source": "rest",
 "request": {
 "prompt": ["{{text}}", "{{..}}"]
 …
 },
 …
}
```

This field is mandatory when using the `rest` embedder.

This field is incompatible with all other embedders.

##### `response`

`response` must be a JSON object with the same structure and data of the response you expect to receive from your `rest` embedder.

The field containing the embedding itself must be replaced with `"{{embedding}}"`:

```json
{
 "source": "rest",
 "response": {
 "data": "{{embedding}}"
 …
 },
 …
}
```

If a single response includes multiple embeddings, the field containing the embedding itself must be an array with two items. One must declare the location and structure of a single embedding, while the second item should be `"{{..}}"`:

```json
{
 "source": "rest",
 "response": {
 "data": [
 {
 "embedding": "{{embedding}}"
 },
 "{{..}}"
 ]
 …
 },
 …
}
```

This field is mandatory when using the `rest` embedder.

This field is incompatible with all other embedders.

##### `distribution`

For mathematical reasons, the `_rankingScore` of semantic search results tend to be closely grouped around an average value that depends on the embedder and model used. This may result in relevant semantic hits being underrepresented and irrelevant semantic hits being overrepresented compared with keyword search hits.

Use `distribution` when configuring an embedder to correct the returned `_rankingScore`s of the semantic hits with an affine transformation:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/indexes/INDEX_NAME/settings' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "embedders": {
 "default": {
 "source": "huggingFace",
 "model": "MODEL_NAME",
 "distribution": {
 "mean": 0.7,
 "sigma": 0.3
 }
 }
 }
 }'
```

Configuring `distribution` requires a certain amount of trial and error, in which you must perform semantic searches and monitor the results. Based on their `rankingScore`s and relevancy, add the observed `mean` and `sigma` values for that index.

`distribution` is an optional field compatible with all embedder sources. It must be an object with two fields:

- `mean`: a number between `0` and `1` indicating the semantic score of "somewhat relevant" hits before using the `distribution` setting
- `sigma`: a number between `0` and `1` indicating the average absolute difference in `_rankingScore`s between "very relevant" hits and "somewhat relevant" hits, and "somewhat relevant" hits and "irrelevant hits".

Changing `distribution` does not trigger a reindexing operation.

##### `headers`

`headers` must be a JSON object whose keys represent the name of additional headers to send in requests to embedders, and whose values represent the value of these additional headers.

By default, Meilisearch sends the following headers with all requests to `rest` embedders:

- `Authorization: Bearer EMBEDDER_API_KEY` (only if `apiKey` was provided)
- `Content-Type: application/json`

If `headers` includes one of these fields, the explicitly declared values take precedence over the defaults.

This field is optional when using the `rest` embedder.

This field is incompatible with all other embedders.

##### `binaryQuantized`

When set to `true`, compresses vectors by representing each dimension with 1-bit values. This reduces the relevancy of semantic search results, but greatly reduces database size.

This option can be useful when working with large Meilisearch projects. Consider activating it if your project contains more than one million documents and uses models with more than 1400 dimensions.

**Activating `binaryQuantized` is irreversible.** Once enabled, Meilisearch converts all vectors and discards all vector data that does fit within 1-bit. The only way to recover the vectors' original values is to re-vectorize the whole index in a new embedder.

##### `pooling`

Configure how Meilisearch should merge individual tokens into a single embedding.

`pooling` must be one of the following strings:

- `"useModel"`: Meilisearch will fetch the pooling method from the model configuration. Default value for new embedders
- `"forceMean"`: always use mean pooling. Default value for embedders created in Meilisearch \<=v1.13
- `"forceCls"`: always use CLS pooling

If in doubt, use `"useModel"`. `"forceMean"` and `"forceCls"` are compatibility options that might be necessary for certain embedders and models.

`pooling` is optional for embedders with the `huggingFace` source.

`pooling` is invalid for all other embedder sources.

##### `indexingEmbedder` and `searchEmbedder` 

When using a [composite embedder](#composite-embedders), configure separate embedders Meilisearch should use when vectorizing documents and search queries.

`indexingEmbedder` often benefits from the higher bandwidth and speed of remote providers so it can vectorize large batches of documents quickly. `searchEmbedder` may often benefits from the lower latency of processing queries locally.

Both fields must be an object and accept the same fields as a regular embedder, with the following exceptions:

- `indexingEmbedder` and `searchEmbedder` must use the same model for generating embeddings
- `indexingEmbedder` and `searchEmbedder` must have identical `dimension`s and `pooling` methods
- `source` is mandatory for both `indexingEmbedder` and `searchEmbedder`
- Neither sub-embedder can set `source` to `composite` or `userProvided`
- Neither `binaryQuantized` and `distribution` are valid sub-embedder fields and must always be declared in the main embedder
- `documentTemplate` and `documentTemplateMaxBytes` are invalid fields for `searchEmbedder`
- `documentTemplate` and `documentTemplateMaxBytes` are mandatory for `indexingEmbedder`, if applicable to its source

`indexingEmbedder` and `searchEmbedder` are mandatory when using the `composite` source.

`indexingEmbedder` and `searchEmbedder` are incompatible with all other embedder sources.

##### `indexingFragments` 

This is an experimental feature. Use the Cloud UI or the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "multimodal": true
 }'
```

`indexingFragments` specifies which fields in your documents should be used to generate multimodal embeddings. It must be an object with the following structure:

```json
 "FRAGMENT_NAME": {
 "value": {
 …
 }
 }
```

`FRAGMENT_NAME` can be any valid string. It must contain a single field, `value`. `value` must then follow your chosen model's specifications.

e.g., for [VoyageAI's multimodal embedding route](https://docs.voyageai.com/reference/multimodal-embeddings-api), `value` must be an object containing a `content` field. `content` itself must contain an array of objects with a `type` field. Depending on `type`'s value, you must include either `text`, `image_url`, or `image_base64`:

```json
{
 "VOYAGE_FRAGMENT_NAME_A": {
 "value": {
 "content": [
 {
 "type": "text",
 "text": "A document called {{doc.title}} that can be described as {{doc.description}}"
 }
 ]
 }
 },
 "VOYAGE_FRAGMENT_NAME_B": {
 "value": {
 "content": [
 {
 "type": "image_url",
 "image_url": "{{doc.image_url}}"
 }
 ]
 }
 },
}
```

Use Liquid templates to interpolate document data into the fragment fields, where `doc` gives you access to all fields within a document.

If a Liquid template appearing inside of a fragment cannot be rendered, no embedding will be generated for that fragment and that document. If a document has no indexing fragments, it will not be returned in multimodal searches. In most cases, a fragment is not rendered because a field it references is missing in the document.

This is different from embeddings based on `documentTemplate`, which abort the indexing task if the document template cannot be rendered for a document.

You can check which documents have embeddings for a given fragment using [vector filters](/learn/filtering_and_sorting/filter_expression_reference#vector-filters).

`indexingFragments` is optional when using the `rest` source.

`indexingFragments` is incompatible with all other embedder sources.

Specifying a `documentTemplate` in an embedder using `indexingFragments` will result in an error.

You must specify at least one valid fragment in `searchFragments` when using `indexingFragments`.

##### `searchFragments` 

This is an experimental feature. Use the Cloud UI or the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "multimodal": true
 }'
```

`searchFragments` instructs Meilisearch how to parse fields present in a query's [`media` search parameter](/reference/api/search#media). It must be an object following the same structure as the [`indexingFragments`](/reference/api/settings#indexingfragments) object:

```json
 "FRAGMENT_NAME": {
 "value": {
 …
 }
 }
```

As with `indexingFragments`, the content of `value` should follow your model's specification.

Use Liquid templates to interpolate search query data into the fragment fields, where `{{media.*}}` gives you access to all [multimodal data received with a query](/reference/api/search#media) and `{{q}}` gives you access to the regular textual query:

```json
{
 "SEARCH_FRAGMENT_A": {
 "value": {
 "content": [
 {
 "type": "image_base64",
 "image_base64": "data:{{media.image.mime}};base64,{{media.image.data}}"
 }
 ]
 }
 },
 "SEARCH_FRAGMENT_B": {
 "value": {
 "content": [
 {
 "type": "text",
 "text": "{{q}}"
 }
 ]
 }
 }
}
```

`searchFragments` is optional when using the `rest` source.

`searchFragments` is incompatible with all other embedder sources.

You must specify at least one valid fragment in `indexingFragments` when using `searchFragments`.

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "kitchenware",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2024-05-11T09:33:12.691402Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset embedder settings

Removes all embedders from your index.

To remove a single embedder, use the [update embedder settings endpoint](#update-embedder-settings) and set the target embedder to `null`.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "books",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2022-04-14T20:53:32.863107Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Chat 

This is an experimental feature. Use the Cloud UI or the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'http://localhost:7700/experimental-features/' \
 -H 'Authorization: Bearer MEILISEARCH_API_KEY' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "chatCompletions": true
 }'
```

The chat settings allow you to configure how your index integrates with Meilisearch's conversational search feature.

### Chat object

```json
{
 "description": "A comprehensive movie database containing titles, overviews, genres, and release dates to help users find movies",
 "documentTemplate": "{% for field in fields %}{% if field.is_searchable and field.value != nil %}{{ field.name }}: {{ field.value }}\n{% endif %}{% endfor %}",
 "documentTemplateMaxBytes": 400,
 "searchParameters": {
 "hybrid": { "embedder": "my-embedder" },
 "limit": 20
 }
}
```

The chat object may contain the following fields: | Name | Type | Default Value | Description | | --- | --- | --- | --- | | **`description`** | String | Empty | The description of the index. Helps the LLM decide which index to use when generating answers | | **`documentTemplate`** | String | `{% for field in fields %} {% if field.is_searchable and not field.value == nil %}{{ field.name }}: {{ field.value }} {% endif %} {% endfor %}` | Template defining the data Meilisearch sends to the LLM | | **`documentTemplateMaxBytes`** | Integer | 400 | Maximum allowed size of rendered document template | | **`searchParameters`** | Object | Empty | The search parameters to use when LLM is performing search requests | ### Search parameters object

Must be one of the following [search parameters](/reference/api/search#search-parameters-object):

- **`hybrid`**
- **`limit`**
- **`sort`**
- **`distinct`**
- **`matchingStrategy`**
- **`attributesToSearchOn`**
- **`rankingScoreThreshold`**

### Get index chat settings

Get the index chat settings configured for an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

[cURL example omitted]

##### Response: `200 OK`

```json
{
 "description": "",
 "documentTemplate": "{% for field in fields %} {% if field.is_searchable and not field.value == nil %}{{ field.name }}: {{ field.value }} {% endif %} {% endfor %}",
 "documentTemplateMaxBytes": 400,
 "searchParameters": {}
}
```

### Update index chat settings

Partially update the index chat settings for an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```json
{
 "description": ,
 "documentTemplate": ,
 "documentTemplateMaxBytes": ,
 "searchParameters": {
 "hybrid": ,
 "limit": ,
 "sort": [, , … ],
 "distinct": ,
 "matchingStrategy": ,
 "attributesToSearchOn": [, , … ],
 "rankingScoreThreshold": ,
 }
}
```

#### Example

[cURL example omitted]

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "movies",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2024-05-11T09:33:12.691402Z"
}
```

You can use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

## Vector store 

This is an experimental feature. On Cloud, contact support to activate it. On OSS, use the experimental features endpoint:

```sh
curl \
 -X PATCH 'http://localhost:7700/experimental-features/' \
 -H 'Authorization: Bearer MEILISEARCH_API_KEY' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "vectorStoreSetting": true
 }'
```

Use `vectorStore` to switch between the `stable` and `experimental` vector store.

The experimental vector store may improve performance in large Meilisearch databases that make heavy use of AI-powered search features.

### Get vector store settings

Get the vector store of an index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `200 OK`

```json
"stable"
```

### Update vector store settings

Update the vector store of an index.

When switching between vector stores, Meilisearch must convert all vector data for use with the new backend. This operation may take a significant amount of time in existing indexes. If a conversion is taking too long, create a new empty index, set its store to `experimental`, and add your documents.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Body

```
"stable" | "experimental"
```

#### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_UID",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2024-07-19T22:33:18.523881Z"
}
```

Use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

### Reset vector store settings

Reset an index's vector store to its default settings.

If you had set `vectorStore` to anything other than the default value, resetting triggers a convertion operation. This operation may take a significant amount of time depending on the size of the index.

#### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | #### Example

##### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_UID",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2024-07-19T22:35:33.723983Z"
}
```

Use the returned `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task).

---

## Similar documents

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesGetSimilarGet1 from '/snippets/samples/code_samples_get_similar_get_1.mdx';
import CodeSamplesGetSimilarPost1 from '/snippets/samples/code_samples_get_similar_post_1.mdx';

The `/similar` route uses AI-powered search to return a number of documents similar to a target document.

Meilisearch exposes two routes for retrieving similar documents: POST and GET. In the majority of cases, POST will offer better performance and ease of use.

## Get similar documents with POST

Retrieve documents similar to a specific search result.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Body | Parameter | Type | Default value | Description | | --- | --- | --- | --- | | **`id`** | String or number | `null` | Identifier of the target document (mandatory) | | **[`embedder`](/reference/api/search#hybrid-search)** | String | `null` | Embedder to use when computing recommendations. Mandatory | | **[`attributesToRetrieve`](/reference/api/search#attributes-to-retrieve)** | Array of strings | `["*"]` | Attributes to display in the returned documents| | **[`offset`](/reference/api/search#offset)** | Integer | `0` | Number of documents to skip | | **[`limit`](/reference/api/search#limit)** | Integer | `20` | Maximum number of documents returned | | **[`filter`](/reference/api/search#filter)** | String | `null` | Filter queries by an attribute's value | | **[`showRankingScore`](/reference/api/search#ranking-score)** | Boolean | `false` | Display the global ranking score of a document | | **[`showRankingScoreDetails`](/reference/api/search#ranking-score-details)** | Boolean | `false` | Display detailed ranking score information | | **[`rankingScoreThreshold`](/reference/api/search#ranking-score-threshold)** | Number | `null` | Exclude results with low ranking scores | | **[`retrieveVectors`](/reference/api/search#display-_vectors-in-response)** | Boolean | `false` | Return document vector data | ### Example

#### Response: `200 OK`

```json
{
 "hits": [
 {
 "id": "299537",
 "title": "Captain Marvel"
 },
 {
 "id": "166428",
 "title": "How to Train Your Dragon: The Hidden World"
 }
 {
 "id": "287947",
 "title": "Shazam!"
 }
 ],
 "id": "23",
 "processingTimeMs": 0,
 "limit": 20,
 "offset": 0,
 "estimatedTotalHits": 3
}
```

## Get similar documents with GET

Retrieve documents similar to a specific search result.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Query parameters | Parameter | Type | Default value | Description | | --- | --- | --- | --- | | **`id`** | String or number | `null` | Identifier of the target document (mandatory) | | **[`embedder`](/reference/api/search#hybrid-search)** | String | `"default"` | Embedder to use when computing recommendations. Mandatory | | **[`attributesToRetrieve`](/reference/api/search#attributes-to-retrieve)** | Array of strings | `["*"]` | Attributes to display in the returned documents| | **[`offset`](/reference/api/search#offset)** | Integer | `0` | Number of documents to skip | | **[`limit`](/reference/api/search#limit)** | Integer | `20` | Maximum number of documents returned | | **[`filter`](/reference/api/search#filter)** | String | `null` | Filter queries by an attribute's value | | **[`showRankingScore`](/reference/api/search#ranking-score)** | Boolean | `false` | Display the global ranking score of a document | | **[`showRankingScoreDetails`](/reference/api/search#ranking-score-details)** | Boolean | `false` | Display detailed ranking score information | | **[`rankingScoreThreshold`](/reference/api/search#ranking-score-threshold)** | Number | `null` | Exclude results with low ranking scores | | **[`retrieveVectors`](/reference/api/search#display-_vectors-in-response)** | Boolean | `false` | Return document vector data | ### Example

#### Response: `200 OK`

```json
{
 "hits": [
 {
 "id": "299537",
 "title": "Captain Marvel"
 },
 {
 "id": "166428",
 "title": "How to Train Your Dragon: The Hidden World"
 }
 {
 "id": "287947",
 "title": "Shazam!"
 }
 ],
 "id": "23",
 "processingTimeMs": 0,
 "limit": 20,
 "offset": 0,
 "estimatedTotalHits": 3
}
```

---

## Snapshots

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesCreateSnapshot1 from '/snippets/samples/code_samples_create_snapshot_1.mdx';

The `/snapshot` route allows you to create database snapshots. Snapshots are `.snapshot` files that can be used to make quick backups of Meilisearch data.

[Learn more about snapshots.](/learn/data_backup/snapshots)

Cloud does not support the `/snapshots` route.

## Create a snapshot

Triggers a snapshot creation task. Once the process is complete, Meilisearch creates a snapshot in the [snapshot directory](/learn/self_hosted/configure_meilisearch_at_launch#snapshot-destination). If the snapshot directory does not exist yet, it will be created.

Snapshot tasks take priority over other tasks in the queue.

[Learn more about asynchronous operations](/learn/async/asynchronous_operations).

### Example

#### Response: `202 Accepted`

```json
{
 "taskUid": 1,
 "indexUid": null,
 "status": "enqueued",
 "type": "snapshotCreation",
 "enqueuedAt": "2023-06-21T11:09:36.417758Z"
}
```

You can use this `taskUid` to get more details on [the status of the task](/reference/api/tasks#get-one-task)

---

## Stats

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesGetIndexStats1 from '/snippets/samples/code_samples_get_index_stats_1.mdx';
import CodeSamplesGetIndexesStats1 from '/snippets/samples/code_samples_get_indexes_stats_1.mdx';

The `/stats` route gives extended information and metrics about indexes and the Meilisearch database.

## Stats object

```json
{
 "databaseSize": 447819776,
 "usedDatabaseSize": 196608,
 "lastUpdate": "2019-11-15T11:15:22.092896Z",
 "indexes": {
 "movies": {
 "numberOfDocuments": 19654,
 "numberOfEmbeddedDocuments": 1,
 "numberOfEmbeddings": 1,
 "rawDocumentDbSize": 5320,
 "avgDocumentSize": 92,
 "isIndexing": false,
 "fieldDistribution": {
 "poster": 19654,
 "overview": 19654,
 "title": 19654,
 "id": 19654,
 "release_date": 19654
 }
 },
 "books": {
 "numberOfDocuments": 5,
 "numberOfEmbeddedDocuments": 5,
 "numberOfEmbeddings": 10,
 "rawDocumentDbSize": 8780,
 "avgDocumentSize": 422,
 "isIndexing": false,
 "fieldDistribution": {
 "id": 5,
 "title": 5,
 "author": 5,
 "price": 5, 
 "genres": 5
 }
 }
 }
}
``` | Name | Type | Description | | --- | --- | --- | | **`databaseSize`** | Integer | Storage space claimed by Meilisearch and LMDB in bytes | | **`usedDatabaseSize`** | Integer | Storage space used by the database in bytes, excluding unused space claimed by LMDB | | **`lastUpdate`** | String | When the last update was made to the database in the [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format | | **`indexes`** | Object | Object containing the statistics for each index found in the database | | **`numberOfDocuments`** | Integer | Total number of documents in an index | | **`numberOfEmbeddedDocuments`** | Integer | Total number of documents with at least one embedding | | **`numberOfEmbeddings`** | Integer | Total number of embeddings in an index | | **`rawDocumentDbSize`** | Integer | Storage space claimed by all documents in the index in bytes | | **`avgDocumentDbSize`** | Integer | Total size of the documents stored in an index divided by the number of documents in that same index | | **`isIndexing`** | Boolean | If `true`, the index is still processing documents and attempts to search will result in undefined behavior | | **`fieldDistribution`** | Object | Shows every field in the index along with the total number of documents containing that field in said index | `fieldDistribution` is not impacted by `searchableAttributes` or `displayedAttributes`. Even if a field is not displayed or searchable, it will still appear in the `fieldDistribution` object. 

## Get stats of all indexes

Get stats of all indexes.

### Example

#### Response: `200 Ok`

```json
{
 "databaseSize": 447819776,
 "usedDatabaseSize": 196608,
 "lastUpdate": "2019-11-15T11:15:22.092896Z",
 "indexes": {
 "movies": {
 "numberOfDocuments": 19654,
 "numberOfEmbeddedDocuments": 1,
 "numberOfEmbeddings": 1,
 "rawDocumentDbSize": 2087,
 "avgDocumentSize": 41,
 "isIndexing": false,
 "fieldDistribution": {
 "poster": 19654,
 "overview": 19654,
 "title": 19654,
 "id": 19654,
 "release_date": 19654
 }
 },
 "books": {
 "numberOfDocuments": 5,
 "numberOfEmbeddedDocuments": 5,
 "numberOfEmbeddings": 10,
 "isIndexing": false,
 "fieldDistribution": {
 "id": 5,
 "title": 5,
 "author": 5,
 "price": 5, 
 "genres": 5
 }
 }
 }
}
```

## Get stats of an index

Get stats of an index.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`index_uid`** * | String | [`uid`](/learn/getting_started/indexes#index-uid) of the requested index | ### Example

#### Response: `200 Ok`

```json
{
 "numberOfDocuments": 19654,
 "numberOfEmbeddedDocuments": 1,
 "numberOfEmbeddings": 1,
 "rawDocumentDbSize": 3618,
 "avgDocumentSize": 104,
 "isIndexing": false,
 "fieldDistribution": {
 "poster": 19654,
 "overview": 19654,
 "title": 19654,
 "id": 19654,
 "release_date": 19654
 }
}
```

---

## Tasks

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'
import { NoticeTag } from '/snippets/notice_tag.mdx';

import CodeSamplesCancelTasks1 from '/snippets/samples/code_samples_cancel_tasks_1.mdx';
import CodeSamplesDeleteTasks1 from '/snippets/samples/code_samples_delete_tasks_1.mdx';
import CodeSamplesGetAllTasks1 from '/snippets/samples/code_samples_get_all_tasks_1.mdx';
import CodeSamplesGetTask1 from '/snippets/samples/code_samples_get_task_1.mdx';

The `/tasks` route gives information about the progress of [asynchronous operations](/learn/async/asynchronous_operations).

## Task object

```json
{
 "uid": 4,
 "batchUids": 0,
 "indexUid": "movie",
 "status": "failed",
 "type": "indexDeletion",
 "canceledBy": null,
 "details": {
 "deletedDocuments": 0
 },
 "error": {
 "message": "Index `movie` not found.",
 "code": "index_not_found",
 "type": "invalid_request",
 "link": "https://docs.meilisearch.com/errors#index_not_found"
 },
 "duration": "PT0.001192S",
 "enqueuedAt": "2022-08-04T12:28:15.159167Z",
 "startedAt": "2022-08-04T12:28:15.161996Z",
 "finishedAt": "2022-08-04T12:28:15.163188Z"
}
```

### `uid`

**Type**: Integer<br />
**Description**: Unique sequential identifier of the task.

The task `uid` is incremented across all indexes in an instance.

### `batchUid`

**Type**: Integer<br />
**Description**: Unique sequential identifier of the batch this task belongs to.

The batch `uid` is incremented across all indexes in an instance.

### `indexUid`

**Type**: String<br />
**Description**: Unique identifier of the targeted index

This value is always `null` for [global tasks](/learn/async/asynchronous_operations#global-tasks).

### `status`

**Type**: String<br />
**Description**: Status of the task. Possible values are `enqueued`, `processing`, `succeeded`, `failed`, and `canceled`

### `type`

**Type**: String<br />
**Description**: Type of operation performed by the task. Possible values are `indexCreation`, `indexUpdate`, `indexDeletion`, `indexSwap`, `documentAdditionOrUpdate`, `documentDeletion`, `settingsUpdate`, `dumpCreation`, `taskCancelation`, `taskDeletion`, `upgradeDatabase`, `documentEdition`, and `snapshotCreation`

### `canceledBy`

**Type**: Integer<br />
**Description**: If the task was canceled, `canceledBy` contains the `uid` of a `taskCancelation` task. If the task was not canceled, `canceledBy` is always `null`

### `details`

**Type**: Object<br />
**Description**: Detailed information on the task payload. This object's contents depend on the task's `type`

#### `documentAdditionOrUpdate` | Name | Description | | :--- | :--- | | **`receivedDocuments`** | Number of documents received | | **`indexedDocuments`** | Number of documents indexed. `null` while the task status is `enqueued` or `processing` | #### `documentDeletion` | Name | Description | | :--- | :--- | | **`providedIds`** | Number of documents queued for deletion | | **`originalFilter`** | The filter used to delete documents. `null` if it was not specified | | **`deletedDocuments`** | Number of documents deleted. `null` while the task status is `enqueued` or `processing` | #### `indexCreation` | Name | Description | | :--- | :--- | | **`primaryKey`** | Value of the `primaryKey` field supplied during index creation. `null` if it was not specified | #### `indexUpdate` | Name | Description | | :--- | :--- | | **`primaryKey`** | Value of the `primaryKey` field supplied during index update. `null` if it was not specified | #### `indexDeletion` | Name | Description | | :--- | :--- | | **`deletedDocuments`** | Number of deleted documents. This should equal the total number of documents in the deleted index. `null` while the task status is `enqueued` or `processing` | #### `indexSwap` | Name | Description | | :--- | :--- | | **`swaps`** | Object containing the payload for the `indexSwap` task | #### `settingsUpdate` | Name | Description | | :--- | :--- | | **`rankingRules`** | List of ranking rules | | **`filterableAttributes`** | List of filterable attributes | | **`distinctAttribute`** | The distinct attribute | | **`searchableAttributes`** | List of searchable attributes | | **`displayedAttributes`** | List of displayed attributes | | **`sortableAttributes`** | List of sortable attributes | | **`stopWords`** | List of stop words | | **`synonyms`** | List of synonyms | | **`typoTolerance`** | The `typoTolerance` object | | **`pagination`** | The `pagination` object | | **`faceting`** | The `faceting` object | #### `dumpCreation` | Name | Description | | :--- | :--- | | **`dumpUid`** | The generated `uid` of the dump. This is also the name of the generated dump file. `null` when the task status is `enqueued`, `processing`, `canceled`, or `failed` | #### `taskCancelation` | Name | Description | | :--- | :--- | | **`matchedTasks`** | The number of matched tasks. If the API key used for the request doesn’t have access to an index, tasks relating to that index will not be included in `matchedTasks` | | **`canceledTasks`** | The number of tasks successfully canceled. If the task cancellation fails, this will be `0`. `null` when the task status is `enqueued` or `processing` | | **`originalFilter`** | The filter used in the [cancel task](#cancel-tasks) request | Task cancellation can be successful and still have `canceledTasks: 0`. This happens when `matchedTasks` matches finished tasks (`succeeded`, `failed`, or `canceled`).

#### `taskDeletion` | Name | Description | | :--- | :--- | | **`matchedTasks`** | The number of matched tasks. If the API key used for the request doesn’t have access to an index, tasks relating to that index will not be included in `matchedTasks` | | **`deletedTasks`** | The number of tasks successfully deleted. If the task deletion fails, this will be `0`. `null` when the task status is `enqueued` or `processing` | | **`originalFilter`** | The filter used in the [delete task](#delete-tasks) request | Task deletion can be successful and still have `deletedTasks: 0`. This happens when `matchedTasks` matches `enqueued` or `processing` tasks.

#### `snapshotCreation`

The `details` object is set to `null` for `snapshotCreation` tasks.

### `error`

**Type**: Object<br />
**Description**: If the task has the `failed` [status](#status), then this object contains the error definition. Otherwise, set to `null` | Name | Description | | :--- | :--- | | **`message`** | A human-readable description of the error | | **`code`** | The [error code](/reference/errors/error_codes) | | **`type`** | The [error type](/reference/errors/overview#errors) | | **`link`** | A link to the relevant section of the documentation | ### `network` 

**Type**: Object<br />
**Description**: If the task was replicated from another remote or to other remotes, `network` will contain information about the remote task uids corresponding to this task. Otherwise, missing in task object.

`network` either has a single key i.e. either `origin` or `remotes`. | Name | Description | | :---| :---| | **`origin`** | The task and remote from which this task was replicated **from** | | **`remotes`** | This task was replicated **to** these tasks and remotes | `origin` is itself an object with keys: | Name | Description | | :--- | :---| | **`remoteName`** | The name of the [remote](/reference/api/network) | | **`taskUid`** | The uid of the task of origin | `remotes` is itself an object whose keys are the [remotes](/reference/api/network) and values an object with a single key i.e. either `task_uid` or `error`: | Name | Description | | :--- | :---| | **`task_uid`** | The uid of the replicated task | | **`error`** | A human-readable error message indicating why the task could not be replicated to that remote | This is an experimental feature. Use the Cloud UI or the experimental features endpoint to activate it:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/experimental-features/' \
 -H 'Content-Type: application/json' \
 --data-binary '{
 "network": true
 }'
```

### `duration`

**Type**: String<br />
**Description**: The total elapsed time the task spent in the `processing` state, in [ISO 8601](https://www.ionos.com/digitalguide/websites/web-development/iso-8601/) format

### `enqueuedAt`

**Type**: String<br />
**Description**: The date and time when the task was first `enqueued`, in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format

### `startedAt`

**Type**: String<br />
**Description**: The date and time when the task began `processing`, in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format

### `finishedAt`

**Type**: String<br />
**Description**: The date and time when the task finished `processing`, whether `failed`, `succeeded`, or `canceled`, in [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format

### `customMetadata`

**Type**: String<br />
**Description**: An arbitrary string optionally configured for tasks adding, updating, and deleting documents. Commonly used to keep track of which documents were processed in a specific task.

### Summarized task object

When an API request triggers an asynchronous process, Meilisearch returns a summarized task object. This object contains the following fields: | Field | Type | Description | | :--- | :--- | :--- | | **`taskUid`** | Integer | Unique sequential identifier | | **`indexUid`** | String | Unique index identifier (always `null` for [global tasks](/learn/async/asynchronous_operations#global-tasks)) | | **`status`** | String | Status of the task. Value is `enqueued` | | **`type`** | String | Type of task | | **`enqueuedAt`** | String | Represents the date and time in the [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format when the task has been `enqueued` | You can use this `taskUid` to get more details on [the status of the task](#get-one-task).

## Get tasks

List all tasks globally, regardless of index. The `task` objects are contained in the `results` array.

Tasks are always returned in descending order of `uid`. This means that by default, **the most recently created `task` objects appear first**.

Task results are [paginated](/learn/async/paginating_tasks) and can be [filtered](/learn/async/filtering_tasks).

### Query parameters | Query Parameter | Default Value | Description | | :--- | :--- | :--- | | **`uids`** | `*` (all uids) | [Filter tasks](/learn/async/filtering_tasks) by their `uid`. Separate multiple task `uids` with a comma (`,`) | | **`batchUids`** | `*` (all batch uids) | [Filter tasks](/learn/async/filtering_tasks) by their `batchUid`. Separate multiple `batchUids` with a comma (`,`) | | **`statuses`** | `*` (all statuses) | [Filter tasks](/learn/async/filtering_tasks) by their `status`. Separate multiple task `statuses` with a comma (`,`) | | **`types`** | `*` (all types) | [Filter tasks](/learn/async/filtering_tasks) by their `type`. Separate multiple task `types` with a comma (`,`) | | **`indexUids`** | `*` (all indexes) | [Filter tasks](/learn/async/filtering_tasks) by their `indexUid`. Separate multiple task `indexUids` with a comma (`,`). Case-sensitive | | **`limit`** | `20` | Number of tasks to return | | **`from`** | `uid` of the last created task | `uid` of the first task returned | | **`reverse`** | `false` | If `true`, returns results in the reverse order, from oldest to most recent | | **`canceledBy`** | N/A | [Filter tasks](/learn/async/filtering_tasks) by their `canceledBy` field. Separate multiple task `uids` with a comma (`,`) | | **`beforeEnqueuedAt`** | `*` (all tasks) | [Filter tasks](/learn/async/filtering_tasks) by their `enqueuedAt` field | | **`beforeStartedAt`** | `*` (all tasks) | [Filter tasks](/learn/async/filtering_tasks) by their `startedAt` field | | **`beforeFinishedAt`** | `*` (all tasks) | [Filter tasks](/learn/async/filtering_tasks) by their `finishedAt` field | | **`afterEnqueuedAt`** | `*` (all tasks) | [Filter tasks](/learn/async/filtering_tasks) by their `enqueuedAt` field | | **`afterStartedAt`** | `*` (all tasks) | [Filter tasks](/learn/async/filtering_tasks) by their `startedAt` field | | **`afterFinishedAt`** | `*` (all tasks) | [Filter tasks](/learn/async/filtering_tasks) by their `finishedAt` field | ### Response | Name | Type | Description | | :--- | :--- | :--- | | **`results`** | Array | An array of [task objects](#task-object) | | **`total`** | Integer | Total number of tasks matching the filter or query | | **`limit`** | Integer | Number of tasks returned | | **`from`** | Integer | `uid` of the first task returned | | **`next`** | Integer | Value passed to `from` to view the next "page" of results. When the value of `next` is `null`, there are no more tasks to view | ### Example

#### Response: `200 Ok`

```json
{
 "results": [
 {
 "uid": 1,
 "indexUid": "movies_reviews",
 "status": "failed",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 100,
 "indexedDocuments": 0
 },
 "error": null,
 "duration": null,
 "enqueuedAt": "2021-08-12T10:00:00.000000Z",
 "startedAt": null,
 "finishedAt": null
 },
 {
 "uid": 0,
 "indexUid": "movies",
 "status": "succeeded",
 "type": "documentAdditionOrUpdate",
 "canceledBy": null,
 "details": {
 "receivedDocuments": 100,
 "indexedDocuments": 100
 },
 "error": null,
 "duration": "PT16S",
 "enqueuedAt": "2021-08-11T09:25:53.000000Z",
 "startedAt": "2021-08-11T10:03:00.000000Z",
 "finishedAt": "2021-08-11T10:03:16.000000Z"
 }
 ],
 "total": 50,
 "limit": 20,
 "from": 1,
 "next": null
}
```

## Get one task

Get a single task.

If you try retrieving a deleted task, Meilisearch will return a [`task_not_found`](/reference/errors/error_codes#task_not_found) error.

### Path parameters | Name | Type | Description | | :--- | :--- | :--- | | **`task_uid`** * | String | [`uid`](#uid) of the requested task | ### Example

#### Response: `200 Ok`

```json
{
 "uid": 1,
 "indexUid": "movies",
 "status": "succeeded",
 "type": "settingsUpdate",
 "canceledBy": null,
 "details": {
 "rankingRules": [
 "typo",
 "ranking:desc",
 "words",
 "proximity",
 "attribute",
 "exactness"
 ]
 },
 "error": null,
 "duration": "PT1S",
 "enqueuedAt": "2021-08-10T14:29:17.000000Z",
 "startedAt": "2021-08-10T14:29:18.000000Z",
 "finishedAt": "2021-08-10T14:29:19.000000Z"
}
```

## Cancel tasks

Cancel any number of `enqueued` or `processing` tasks based on their `uid`, `status`, `type`, `indexUid`, or the date at which they were enqueued (`enqueuedAt`) or processed (`startedAt`).

Task cancellation is an atomic transaction: **either all tasks are successfully canceled or none are**.

To prevent users from accidentally canceling all enqueued and processing tasks, Meilisearch throws the [`missing_task_filters`](/reference/errors/error_codes#missing_task_filters) error if this route is used without any filters (`POST /tasks/cancel`).

You can also cancel `taskCancelation` type tasks as long as they are in the `enqueued` or `processing` state. This is possible because `taskCancelation` type tasks are processed in reverse order, such that the last one you enqueue will be processed first.

### Query parameters

A valid `uids`, `statuses`, `types`, `indexUids`, or date(`beforeXAt` or `afterXAt`) parameter is required. | Query Parameter | Description | | :--- | :--- | | **`uids`** | Cancel tasks based on `uid`. Separate multiple `uids` with a comma (`,`). Use `uids=*` for all `uids` | | **`statuses`** | Cancel tasks based on `status`. Separate multiple `statuses` with a comma (`,`). Use `statuses=*` for all `statuses` | | **`types`** | Cancel tasks based on `type`. Separate multiple `types` with a comma (`,`). Use `types=*` for all `types` | | **`indexUids`** | Cancel tasks based on `indexUid`. Separate multiple `uids` with a comma (`,`). Use `indexUids=*` for all `indexUids`. Case-sensitive | | **`beforeEnqueuedAt`** | Cancel tasks **before** a specified `enqueuedAt` date. Use `beforeEnqueuedAt=*` to cancel all tasks | | **`beforeStartedAt`** | Cancel tasks **before** a specified `startedAt` date. Use `beforeStartedAt=*` to cancel all tasks | | **`afterEnqueuedAt`** | Cancel tasks **after** a specified `enqueuedAt` date. Use `afterEnqueuedAt=*` to cancel all tasks | | **`afterStartedAt`** | Cancel tasks **after** a specified `startedAt` date. Use `afterStartedAt=*` to cancel all tasks | Date filters are equivalent to `<` or `>` operations. At this time, there is no way to perform a `≤` or `≥` operations with a date filter.

[To learn more about filtering tasks, refer to our dedicated guide.](/learn/async/filtering_tasks)

### Example

#### Response: `200 Ok`

```json
{
 "taskUid": 3,
 "indexUid": null,
 "status": "enqueued",
 "type": "taskCancelation",
 "enqueuedAt": "2021-08-12T10:00:00.000000Z"
}
```

Since `taskCancelation` is a [global task](/learn/async/asynchronous_operations#global-tasks), its `indexUid` is always `null`.

You can use this `taskUid` to get more details on the [status of the task](#get-one-task).

### Cancel all tasks

You can cancel all `processing` and `enqueued` tasks using the following filter:

The API key used must have access to all indexes (`"indexes": [*]`) and the [`task.cancel`](/reference/api/keys#actions) action.

## Delete tasks

Delete a finished (`succeeded`, `failed`, or `canceled`) task based on `uid`, `status`, `type`, `indexUid`, `canceledBy`, or date. Task deletion is an atomic transaction: **either all tasks are successfully deleted, or none are**.

To prevent users from accidentally deleting the entire task history, Meilisearch throws the [`missing_task_filters`](/reference/errors/error_codes#missing_task_filters) error if this route is used without any filters (DELETE `/tasks`).

### Query parameters

A valid `uids`, `statuses`, `types`, `indexUids`, `canceledBy`, or date(`beforeXAt` or `afterXAt`) parameter is required. | Query Parameter | Description | | :--- | :--- | | **`uids`** | Delete tasks based on `uid`. Separate multiple `uids` with a comma (`,`). Use `uids=*` for all `uids` | | **`statuses`** | Delete tasks based on `status`. Separate multiple `statuses` with a comma (`,`). Use `statuses=*` for all `statuses` | | **`types`** | Delete tasks based on `type`. Separate multiple `types` with a comma (`,`). Use `types=*` for all `types` | | **`indexUids`** | Delete tasks based on `indexUid`. Separate multiple `uids` with a comma (`,`). Use `indexUids=*` for all `indexUids`. Case-sensitive | | **`canceledBy`** | Delete tasks based on the `canceledBy` field | | **`beforeEnqueuedAt`** | Delete tasks **before** a specified `enqueuedAt` date. Use `beforeEnqueuedAt=*` to delete all tasks | | **`beforeStartedAt`** | Delete tasks **before** a specified `startedAt` date. Use `beforeStartedAt=*` to delete all tasks | | **`beforeFinishedAt`** | Delete tasks **before** a specified `finishedAt` date. Use `beforeFinishedAt=*` to delete all tasks | | **`afterEnqueuedAt`** | Delete tasks **after** a specified `enqueuedAt` date. Use `afterEnqueuedAt=*` to delete all tasks | | **`afterStartedAt`** | Delete tasks **after** a specified `startedAt` date. Use `afterStartedAt=*` to delete all tasks | | **`afterFinishedAt`** | Delete tasks **after** a specified `finishedAt` date. Use `afterFinishedAt=*` to delete all tasks | Date filters are equivalent to `<` or `>` operations. At this time, there is no way to perform a `≤` or `≥` operations with a date filter.

[To learn more about filtering tasks, refer to our dedicated guide.](/learn/async/filtering_tasks)

### Example

#### Response: `200 Ok`

```json
{
 "taskUid": 3,
 "indexUid": null,
 "status": "enqueued",
 "type": "taskDeletion",
 "enqueuedAt": "2021-08-12T10:00:00.000000Z"
}
```

Since `taskDeletion` is a [global task](/learn/async/asynchronous_operations#global-tasks), its `indexUid` is always `null`.

You can use this `taskUid` to get more details on the [status of the task](#get-one-task).

### Delete all tasks

You can delete all finished tasks by using the following filter:

The API key used must have access to all indexes (`"indexes": [*]`) and the [`task.delete`](/reference/api/keys#actions) action.

---

## Version

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesGetVersion1 from '/snippets/samples/code_samples_get_version_1.mdx';

The `/version` route allows you to check the version of a running Meilisearch instance.

## Version object | Name | Description | | :--- | :--- | | **`commitSha`** | Commit identifier that tagged the `pkgVersion` release | | **`commitDate`** | Date when the `commitSha` was created | | **`pkgVersion`** | Meilisearch version | ## Get version of Meilisearch Get version of Meilisearch.

### Example

#### Response: `200 Ok`

```json
{
 "commitSha": "b46889b5f0f2f8b91438a08a358ba8f05fc09fc1",
 "commitDate": "2019-11-15T09:51:54.278247+00:00",
 "pkgVersion": "0.1.1"
}
```

---

## Webhooks

import { RouteHighlighter } from '/snippets/route_highlighter.mdx'

import CodeSamplesWebhooksGet1 from '/snippets/samples/code_samples_webhooks_get_1.mdx';
import CodeSamplesWebhooksPost1 from '/snippets/samples/code_samples_webhooks_post_1.mdx';
import CodeSamplesWebhooksPatch1 from '/snippets/samples/code_samples_webhooks_patch_1.mdx';
import CodeSamplesWebhooksDelete1 from '/snippets/samples/code_samples_webhooks_delete_1.mdx';

Use the `/webhooks` to trigger automatic workflows when Meilisearch finishes processing tasks.

## The webhook object

```json
{
 "uuid": "V4_UUID_GENERATED_BY_MEILISEARCH",
 "url": "WEBHOOK_NOTIFICATION_TARGET_URL",
 "headers": {
 "HEADER": "VALUE",
 },
 "isEditable": false
}
```

- `uuid`: a v4 uuid Meilisearch automatically generates when you create a new webhook
- `url`: a string indication the URL Meilisearch should notify whenever it completes a task, required
- `headers`: an object with HTTP headers and their values, optional, often used for authentication
 - `Authorization` headers: the value of authorization headers is redacted in `webhook` responses. Do not use authorization header values as returned by Meilisearch to update a webhook
- `isEditable`: read-only Boolean field indicating whether you can edit the webhook. Meilisearch automatically sets this to `true` for all webhooks created via the API and to `false` for reserved webhooks

## The webhook payload

When Meilisearch finishes processing a task, it sends the relevant [task object](/reference/api/tasks#task-object) to all configured webhooks.

## Get all webhooks

Get a list of all webhooks configured in the current Meilisearch instance.

### Example

#### Response: `200 OK`

```json
{
 "results": [
 {
 "uuid": "UUID_V4",
 "url": "WEBHOOK_TARGET_URL",
 "headers": {
 "HEADER": "VALUE",
 },
 "isEditable": false
 },
 {
 "uuid": "UUID_V4",
 "url": "WEBHOOK_TARGET_URL",
 "headers": null,
 "isEditable": true
 }
 ]
}
```

## Get a single webhook

Get a single webhook configured in the current Meilisearch instance.

### Example

#### Response: `200 OK`

```json
{
 "uuid": "UUID_V4",
 "url": "WEBHOOK_TARGET_URL",
 "headers": {
 "HEADER": "VALUE",
 },
 "isEditable": false
}
```

## Create a webhook

Create a new webhook. When Meilisearch finishes processing a task, it sends the relevant [task object](/reference/api/tasks#task-object) to all configured webhooks.

You can create up to 20 webhooks. Having multiple webhooks active at the same time may negatively impact performance.

### Example

#### Response: `200 OK`

```json
{
 "uuid": "627ea538-733d-4545-8d2d-03526eb381ce",
 "url": "WEBHOOK_TARGET_URL",
 "headers": {
 "authorization": "SECURITY_KEY",
 "referer": "https://example.com",
 },
 "isEditable": true
}
```

## Update a webhook

Update the configuration for the specified webhook. To remove a field, set its value to `null`.

When updating the `headers` field, Meilisearch only changes the headers you have explicitly submitted. All other headers remain unaltered.

It is not possible to edit webhooks whose `isEditable` field is set to `false`.

Cloud may create internal webhooks to support features such as Analytics and monitoring. These webhooks are always `isEditable: false`.

### Example

#### Response: `200 OK`

```json
{
 "uuid": "627ea538-733d-4545-8d2d-03526eb381ce",
 "url": "WEBHOOK_TARGET_URL",
 "headers": {
 "authorization": "SECURITY_KEY"
 },
 "isEditable": true
}
```

## Delete a webhook

Delete a webhook and stop sending task completion data to the target URL.

It is not possible to delete webhooks whose `isEditable` field is set to `false`.

### Example

#### Response: `204 No Content`

---

## Error codes

This page is an exhaustive list of Meilisearch API errors.

## `api_key_already_exists`

A key with this [`uid`](/reference/api/keys#uid) already exists.

## `api_key_not_found`

The requested API key could not be found.

## `bad_request`

The request is invalid, check the error message for more information.

## `batch_not_found`

The requested batch does not exist. Please ensure that you are using the correct [`uid`](/reference/api/batches#uid).

## `database_size_limit_reached`

The requested database has reached its maximum size.

## `document_fields_limit_reached`

A document exceeds the [maximum limit of 65,535 fields](/learn/resources/known_limitations#maximum-number-of-attributes-per-document).

## `document_not_found`

The requested document can't be retrieved. Either it doesn't exist, or the database was left in an inconsistent state.

## `dump_process_failed`

An error occurred during the dump creation process. The task was aborted.

## `facet_search_disabled`

The [`/facet-search`](/reference/api/facet_search) route has been queried while [the `facetSearch` index setting](/reference/api/settings#facet-search) is set to `false`.

## `feature_not_enabled`

You have tried using an [experimental feature](/learn/resources/experimental_features_overview) without activating it.

## `immutable_api_key_actions`

The [`actions`](/reference/api/keys#actions) field of an API key cannot be modified.

## `immutable_api_key_created_at`

The [`createdAt`](/reference/api/keys#createdat) field of an API key cannot be modified.

## `immutable_api_key_expires_at`

The [`expiresAt`](/reference/api/keys#expiresat) field of an API key cannot be modified.

## `immutable_api_key_indexes`

The [`indexes`](/reference/api/keys#indexes) field of an API key cannot be modified.

## `immutable_api_key_key`

The [`key`](/reference/api/keys#key) field of an API key cannot be modified.

## `immutable_api_key_uid`

The [`uid`](/reference/api/keys#uid) field of an API key cannot be modified.

## `immutable_api_key_updated_at`

The [`updatedAt`](/reference/api/keys#updatedat) field of an API key cannot be modified.

## `immutable_index_uid`

The [`uid`](/reference/api/indexes#index-object) field of an index cannot be modified.

## `immutable_index_updated_at`

The [`updatedAt`](/reference/api/indexes#index-object) field of an index cannot be modified.

### `immutable_webhook`

You tried to modify a reserved [webhook](/reference/api/webhooks). Reserved webhooks are configured by Cloud and have `isEditable` set to `true`. Webhooks created with an instance option are also immutable.

### `immutable_webhook_uuid`

You tried to manually set a webhook `uuid`. Meilisearch automatically generates `uuid` for webhooks.

### `immutable_webhook_is_editable`

You tried to manually set a webhook's `isEditable` field. Meilisearch automatically sets `isEditable` for all webhooks. Only reserved webhooks have `isEditable` set to `false`.

## `index_already_exists`

An index with this [`uid`](/reference/api/indexes#index-object) already exists, check out our guide on [index creation](/learn/getting_started/indexes).

## `index_creation_failed`

An error occurred while trying to create an index, check out our guide on [index creation](/learn/getting_started/indexes).

## `index_not_found`

An index with this `uid` was not found, check out our guide on [index creation](/learn/getting_started/indexes).

## `index_primary_key_already_exists`

The requested index already has a primary key that [cannot be changed](/learn/getting_started/primary_key#changing-your-primary-key-with-the-update-index-endpoint).

## `index_primary_key_multiple_candidates_found`

[Primary key inference](/learn/getting_started/primary_key#meilisearch-guesses-your-primary-key) failed because the received documents contain multiple fields ending with `id`. Use the [update index endpoint](/reference/api/indexes#update-an-index) to manually set a primary key.

## `internal`

Meilisearch experienced an internal error. Check the error message, and [open an issue](https://github.com/meilisearch/meilisearch/issues/new?assignees=&labels=&template=bug_report&title=) if necessary.

## `invalid_api_key`

The requested resources are protected with an API key. The provided API key is invalid. Read more about it in our [security tutorial](/learn/security/basic_security).

## `invalid_api_key_actions`

The [`actions`](/reference/api/keys#actions) field for the provided API key resource is invalid. It should be an array of strings representing action names.

## `invalid_api_key_description`

The [`description`](/reference/api/keys#description) field for the provided API key resource is invalid. It should either be a string or set to `null`.

## `invalid_api_key_expires_at`

The [`expiresAt`](/reference/api/keys#expiresat) field for the provided API key resource is invalid. It should either show a future date or datetime in the [RFC 3339](https://www.ietf.org/rfc/rfc3339.txt) format or be set to `null`.

## `invalid_api_key_indexes`

The [`indexes`](/reference/api/keys#indexes) field for the provided API key resource is invalid. It should be an array of strings representing index names.

## `invalid_api_key_limit`

The [`limit`](/reference/api/keys#query-parameters) parameter is invalid. It should be an integer.

## `invalid_api_key_name`

The given [`name`](/reference/api/keys#name) is invalid. It should either be a string or set to `null`.

## `invalid_api_key_offset`

The [`offset`](/reference/api/keys#query-parameters) parameter is invalid. It should be an integer.

## `invalid_api_key_uid`

The given [`uid`](/reference/api/keys#uid) is invalid. The `uid` must follow the [uuid v4](https://www.sohamkamani.com/uuid-versions-explained) format.

## `invalid_search_attributes_to_search_on`

The value passed to [`attributesToSearchOn`](/reference/api/search#customize-attributes-to-search-on-at-search-time) is invalid. `attributesToSearchOn` accepts an array of strings indicating document attributes. Attributes given to `attributesToSearchOn` must be present in the [`searchableAttributes` list](/learn/relevancy/displayed_searchable_attributes#the-searchableattributes-list).

## `invalid_search_media`

The value passed to [`media`](/reference/api/search#media) is not a valid JSON object.

## `invalid_search_media_and_vector`

The search query contains non-`null` values for both [`media`](/reference/api/search#media) and [`vector`](/reference/api/search#media). These two parameters are mutually exclusive, since `media` generates vector embeddings via the embedder configured in `hybrid`.

## `invalid_content_type`

The [Content-Type header](/reference/api/overview#content-type) is not supported by Meilisearch. Currently, Meilisearch only supports JSON, CSV, and NDJSON.

## `invalid_document_csv_delimiter`

The [`csvDelimiter`](/reference/api/documents#add-or-replace-documents) parameter is invalid. It should either be a string or [a single ASCII character](https://www.rfc-editor.org/rfc/rfc20).

## `invalid_document_id`

The provided [document identifier](/learn/getting_started/primary_key#document-id) does not meet the format requirements. A document identifier must be of type integer or string, composed only of alphanumeric characters (a-z A-Z 0-9), hyphens (-), and underscores (_).

## `invalid_document_fields`

The [`fields`](/reference/api/documents#query-parameters) parameter is invalid. It should be a string.

## `invalid_document_filter`

This error occurs if:

- The [`filter`](/reference/api/documents#query-parameters) parameter is invalid
 - It should be a string, array of strings, or array of array of strings for the [get documents with POST endpoint](/reference/api/documents#get-documents-with-post)
 - It should be a string for the [get documents with GET endpoint](/reference/api/documents#get-documents-with-get)
- The attribute used for filtering is not defined in the [`filterableAttributes` list](/reference/api/settings#filterable-attributes)
- The [filter expression](/learn/filtering_and_sorting/filter_expression_reference) has a missing or invalid operator. [Read more about our supported operators](/learn/filtering_and_sorting/filter_expression_reference)

## `invalid_document_limit`

The [`limit`](/reference/api/documents#query-parameters) parameter is invalid. It should be an integer.

## `invalid_document_offset`

The [`offset`](/reference/api/documents#query-parameters) parameter is invalid. It should be an integer.

## `invalid_document_sort`

This error occurs if:

- The syntax for the [`sort`](/reference/api/documents#body) parameter is invalid
- The attribute used for sorting is not defined in the [`sortableAttributes`](/reference/api/settings#sortable-attributes) list or the `sort` ranking rule is missing from the settings
- A reserved keyword like `_geo`, `_geoDistance`, `_geoRadius`, or `_geoBoundingBox` is used as a filter

## `invalid_document_geo_field`

The provided `_geo` field of one or more documents is invalid. Meilisearch expects `_geo` to be an object with two fields, `lat` and `lng`, each containing geographic coordinates expressed as a string or floating point number. Read more about `_geo` and how to troubleshoot it in [our dedicated guide](/learn/filtering_and_sorting/geosearch).

## `invalid_document_geojson_field`

The `geojson` field in one or more documents is invalid or doesn't match the [GeoJSON specification](https://datatracker.ietf.org/doc/html/rfc7946).

## `invalid_export_url`

The export target instance URL is invalid or could not be reached.

## `invalid_export_api_key`

The supplied security key does not have the required permissions to access the target instance.

## `invalid_export_payload_size`

The provided payload size is invalid. The payload size must be a string indicating the maximum payload size in a human-readable format.

## `invalid_export_indexes_patterns`

The provided index pattern is invalid. The index pattern must be an alphanumeric string, optionally including a wildcard.

## `invalid_export_index_filter`

The provided index export filter is not a valid [filter expression](/learn/filtering_and_sorting/filter_expression_reference).

## `invalid_facet_search_facet_name`

The attribute used for the `facetName` field is either not a string or not defined in the [`filterableAttributes` list](/reference/api/settings#filterable-attributes).

## `invalid_facet_search_facet_query`

The provided value for `facetQuery` is invalid. It should either be a string or `null`.

## `invalid_index_limit`

The [`limit`](/reference/api/indexes#query-parameters) parameter is invalid. It should be an integer.

## `invalid_index_offset`

The [`offset`](/reference/api/indexes#query-parameters) parameter is invalid. It should be an integer.

## `invalid_index_uid`

There is an error in the provided index format, check out our guide on [index creation](/learn/getting_started/indexes).

## `invalid_index_primary_key`

The [`primaryKey`](/reference/api/indexes#body-2) field is invalid. It should either be a string or set to `null`.

## `invalid_multi_search_query_federated`

A multi-search query includes `federationOptions` but the top-level `federation` object is `null` or missing.

## `invalid_multi_search_query_pagination`

A multi-search query contains `page`, `hitsPerPage`, `limit` or `offset`, but the top-level federation object is not `null`.

## `invalid_multi_search_query_position`

`federationOptions.queryPosition` is not a positive integer.

## `invalid_multi_search_weight`

A multi-search query contains a negative value for `federated.weight`.

## `invalid_multi_search_queries_ranking_rules`

Two or more queries in a multi-search request have incompatible results.

## `invalid_multi_search_facets`

`federation.facetsByIndex.<INDEX_NAME>` contains a value i.e. not in the filterable attributes list.

## `invalid_multi_search_sort_facet_values_by`

`federation.mergeFacets.sortFacetValuesBy` is not a string or doesn't have one of the allowed values.

## `invalid_multi_search_query_facets`

A query in the queries array contains `facets` when federation is present and non-`null`.

## `invalid_multi_search_merge_facets`

`federation.mergeFacets` is not an object or contains unexpected fields.

## `invalid_multi_search_max_values_per_facet`

`federation.mergeFacets.maxValuesPerFacet` is not a positive integer.

## `invalid_multi_search_facet_order`

Two or more indexes have a different `faceting.sortFacetValuesBy` for the same requested facet.

## `invalid_multi_search_facets_by_index`

`facetsByIndex` is not an object or contains unknown fields.

## `invalid_multi_search_remote`

`federationOptions.remote` is not `network.self` and is not a key in `network.remotes`.

## `invalid_network_self`

The [network object](/reference/api/network#the-network-object) contains a `self` i.e. not a string or `null`.

## `invalid_network_remotes`

The [network object](/reference/api/network#the-network-object) contains a `remotes` i.e. not an object or `null`.

## `invalid_network_url`

One of the remotes in the [network object](/reference/api/network#the-network-object) contains a `url` i.e. not a string.

## `invalid_network_search_api_key`

One of the remotes in the [network object](/reference/api/network#the-network-object) contains a `searchApiKey` i.e. not a string or `null`.

## `invalid_search_attributes_to_crop`

The [`attributesToCrop`](/reference/api/search#attributes-to-crop) parameter is invalid. It should be an array of strings, a string, or set to `null`.

## `invalid_search_attributes_to_highlight`

The [`attributesToHighlight`](/reference/api/search#attributes-to-highlight) parameter is invalid. It should be an array of strings, a string, or set to `null`.

## `invalid_search_attributes_to_retrieve`

The [`attributesToRetrieve`](/reference/api/search#attributes-to-retrieve) parameter is invalid. It should be an array of strings, a string, or set to `null`.

## `invalid_search_crop_length`

The [`cropLength`](/reference/api/search#crop-length) parameter is invalid. It should be an integer.

## `invalid_search_crop_marker`

The [`cropMarker`](/reference/api/search#crop-marker) parameter is invalid. It should be a string or set to `null`.

### `invalid_search_embedder`

[`embedder`](/reference/api/search#hybrid-search) is invalid. It should be a string corresponding to the name of a configured embedder.

## `invalid_search_facets`

This error occurs if:

- The [`facets`](/reference/api/search#facets) parameter is invalid. It should be an array of strings, a string, or set to `null`
- The attribute used for faceting is not defined in the [`filterableAttributes` list](/reference/api/settings#filterable-attributes)

## `invalid_search_filter`

This error occurs if:

- The syntax for the [`filter`](/reference/api/search#filter) parameter is invalid
- The attribute used for filtering is not defined in the [`filterableAttributes` list](/reference/api/settings#filterable-attributes)
- A reserved keyword like `_geo`, `_geoDistance`, or `_geoPoint` is used as a filter

## `invalid_search_highlight_post_tag`

The [`highlightPostTag`](/reference/api/search#highlight-tags) parameter is invalid. It should be a string.

## `invalid_search_highlight_pre_tag`

The [`highlightPreTag`](/reference/api/search#highlight-tags) parameter is invalid. It should be a string.

## `invalid_search_hits_per_page`

The [`hitsPerPage`](/reference/api/search#number-of-results-per-page) parameter is invalid. It should be an integer.

## `invalid_search_hybrid_query`

The [`hybrid`](/reference/api/search#hybrid-search) parameter is neither `null` nor an object, or it is an object with unknown keys.

## `invalid_search_limit`

The [`limit`](/reference/api/search#limit) parameter is invalid. It should be an integer.

## `invalid_search_locales`

The [`locales`](/reference/api/search#query-locales) parameter is invalid.

## `invalid_settings_embedder`

The [`embedders`](/reference/api/settings#embedders) index setting value is invalid.

## `invalid_settings_facet_search`

The [`facetSearch`](/reference/api/settings#facet-search) index setting value is invalid.

## `invalid_settings_localized_attributes`

The [`localizedAttributes`](/reference/api/settings#localized-attributes) index setting value is invalid.

## `invalid_search_matching_strategy`

The [`matchingStrategy`](/reference/api/search#matching-strategy) parameter is invalid. It should either be set to `last` or `all`.

## `invalid_search_offset`

The [`offset`](/reference/api/search#offset) parameter is invalid. It should be an integer.

## `invalid_settings_prefix_search`

The [`prefixSearch`](/reference/api/settings#prefix-search) index setting value is invalid.

## `invalid_search_page`

The [`page`](/reference/api/search#page) parameter is invalid. It should be an integer.

## `invalid_search_q`

The [`q`](/reference/api/search#query-q) parameter is invalid. It should be a string or set to `null`

## `invalid_search_ranking_score_threshold`

The [`rankingScoreThreshold`](/reference/api/search#ranking-score-threshold) in a search or multi-search request is not a number between `0.0` and `1.0`.

## `invalid_search_show_matches_position`

The [`showMatchesPosition`](/reference/api/search#show-matches-position) parameter is invalid. It should either be a boolean or set to `null`.

## `invalid_search_sort`

This error occurs if:

- The syntax for the [`sort`](/reference/api/search#sort) parameter is invalid
- The attribute used for sorting is not defined in the [`sortableAttributes`](/reference/api/settings#sortable-attributes) list or the `sort` ranking rule is missing from the settings
- A reserved keyword like `_geo`, `_geoDistance`, `_geoRadius`, or `_geoBoundingBox` is used as a filter

## `invalid_settings_displayed_attributes`

The value of [displayed attributes](/learn/relevancy/displayed_searchable_attributes#displayed-fields) is invalid. It should be an empty array, an array of strings, or set to `null`.

## `invalid_settings_distinct_attribute`

The value of [distinct attributes](/learn/relevancy/distinct_attribute) is invalid. It should be a string or set to `null`.

## `invalid_settings_faceting_sort_facet_values_by`

The value provided for the [`sortFacetValuesBy`](/reference/api/settings#faceting-object) object is incorrect. The accepted values are `alpha` or `count`.

## `invalid_settings_faceting_max_values_per_facet`

The value for the [`maxValuesPerFacet`](/reference/api/settings#faceting-object) field is invalid. It should either be an integer or set to `null`.

## `invalid_settings_filterable_attributes`

The value of [filterable attributes](/reference/api/settings#filterable-attributes) is invalid. It should be an empty array, an array of strings, or set to `null`.

## `invalid_settings_pagination`

The value for the [`maxTotalHits`](/reference/api/settings#pagination-object) field is invalid. It should either be an integer or set to `null`.

## `invalid_settings_ranking_rules`

This error occurs if:

- The [settings payload](/reference/api/settings#body) has an invalid format
- A non-existent ranking rule is specified
- A custom ranking rule is malformed
- A reserved keyword like `_geo`, `_geoDistance`, `_geoRadius`, `_geoBoundingBox`, or `_geoPoint` is used as a custom ranking rule

## `invalid_settings_searchable_attributes`

The value of [searchable attributes](/reference/api/settings#searchable-attributes) is invalid. It should be an empty array, an array of strings or set to `null`.

## `invalid_settings_search_cutoff_ms`

The specified value for [`searchCutoffMs](/reference/api/settings#search-cutoff) is invalid. It should be an integer indicating the cutoff in milliseconds.

## `invalid_settings_sortable_attributes`

The value of [sortable attributes](/reference/api/settings#sortable-attributes) is invalid. It should be an empty array, an array of strings or set to `null`.

## `invalid_settings_stop_words`

The value of [stop words](/reference/api/settings#stop-words) is invalid. It should be an empty array, an array of strings or set to `null`.

## `invalid_settings_synonyms`

The value of the [synonyms](/reference/api/settings#synonyms) is invalid. It should either be an object or set to `null`.

## `invalid_settings_typo_tolerance`

This error occurs if:

- The [`enabled`](/reference/api/settings#typo-tolerance-object) field is invalid. It should either be a boolean or set to `null`
- The [`disableOnAttributes`](/reference/api/settings#typo-tolerance-object) field is invalid. It should either be an array of strings or set to `null`
- The [`disableOnWords`](/reference/api/settings#typo-tolerance-object) field is invalid. It should either be an array of strings or set to `null`
- The [`minWordSizeForTypos`](/reference/api/settings#typo-tolerance-object) field is invalid. It should either be an integer or set to `null`
- The value of either [`oneTypo`](/reference/api/settings#typo-tolerance-object) or [`twoTypos`](/reference/api/settings#typo-tolerance-object) is invalid. It should either be an integer or set to `null`

## `invalid_similar_id`

The provided target document identifier is invalid. A document identifier can be of type integer or string, only composed of alphanumeric characters (a-z A-Z 0-9), hyphens (-) and underscores (_).

## `not_found_similar_id`

Meilisearch could not find the target document. Make sure your target document identifier corresponds to a document in your index.

## `invalid_similar_attributes_to_retrieve`

[`attributesToRetrieve`](/reference/api/search#attributes-to-retrieve) is invalid. It should be an array of strings, a string, or set to null.

### `invalid_similar_embedder`

[`embedder`](/reference/api/similar#body) is invalid. It should be a string corresponding to the name of a configured embedder.

## `invalid_similar_filter`

[`filter`](/reference/api/search#filter) is invalid or contains a filter expression with a missing or invalid operator. Filter expressions must be a string, array of strings, or array of array of strings for the POST endpoint. It must be a string for the GET endpoint.

Meilisearch also throws this error if the attribute used for filtering is not defined in the `filterableAttributes` list.

## `invalid_similar_limit`

[`limit`](/reference/api/search#limit) is invalid. It should be an integer.

## `invalid_similar_offset`

[`offset`](/reference/api/search#offset) is invalid. It should be an integer.

## `invalid_similar_show_ranking_score`

[`ranking_score`](/reference/api/search#ranking-score) is invalid. It should be a boolean.

## `invalid_similar_show_ranking_score_details`

[`ranking_score_details`](/reference/api/search#ranking-score-details) is invalid. It should be a boolean.

## `invalid_similar_ranking_score_threshold`

The [`rankingScoreThreshold`](/reference/api/search#ranking-score-threshold) in a similar documents request is not a number between `0.0` and `1.0`.

## `invalid_state`

The database is in an invalid state. Deleting the database and re-indexing should solve the problem.

## `invalid_store_file`

The `data.ms` folder is in an invalid state. Your `b` file is corrupted or the `data.ms` folder has been replaced by a file.

## `invalid_swap_duplicate_index_found`

The indexes used in the [`indexes`](/reference/api/indexes#body-2) array for a [swap index](/reference/api/indexes#swap-indexes) request have been declared multiple times. You must declare each index only once.

## `invalid_swap_indexes`

This error happens if:

- The payload doesn't contain exactly two index [`uids`](/reference/api/indexes#body-2) for a swap operation
- The payload contains an invalid index name in the [`indexes`](/reference/api/indexes#body-2) array

## `invalid_task_after_enqueued_at`

The [`afterEnqueuedAt`](/reference/api/tasks#query-parameters) query parameter is invalid.

## `invalid_task_after_finished_at`

The [`afterFinishedAt`](/reference/api/tasks#query-parameters) query parameter is invalid.

## `invalid_task_after_started_at`

The [`afterStartedAt`](/reference/api/tasks#query-parameters) query parameter is invalid.

## `invalid_task_before_enqueued_at`

The [`beforeEnqueuedAt`](/reference/api/tasks#query-parameters) query parameter is invalid.

## `invalid_task_before_finished_at`

The [`beforeFinishedAt`](/reference/api/tasks#query-parameters) query parameter is invalid.

## `invalid_task_before_started_at`

The [`beforeStartedAt`](/reference/api/tasks#query-parameters) query parameter is invalid.

## `invalid_task_canceled_by`

The [`canceledBy`](/reference/api/tasks#canceledby) query parameter is invalid. It should be an integer. Multiple `uid`s should be separated by commas (`,`).

## `invalid_task_index_uids`

The [`indexUids`](/reference/api/tasks#query-parameters) query parameter contains an invalid index uid.

## `invalid_task_limit`

The [`limit`](/reference/api/tasks#query-parameters) parameter is invalid. It must be an integer.

## `invalid_task_statuses`

The requested task status is invalid. Please use one of the [possible values](/reference/api/tasks#status).

## `invalid_task_types`

The requested task type is invalid. Please use one of the [possible values](/reference/api/tasks#type).

## `invalid_task_uids`

The [`uids`](/reference/api/tasks#query-parameters) query parameter is invalid.

### `invalid_webhooks`

The create webhook request did not contain a valid JSON payload. Meilisearch also returns this error when you try to create more than 20 webhooks.

### `invalid_webhook_url`

The provided webhook URL isn’t a valid JSON string, is `null`, is missing, or its value cannot be parsed as a valid URL.

### `invalid_webhook_headers`

The provided webhook `headers` field is not a JSON object or not a valid HTTP header. Meilisearch also returns this error if you set more than 200 header fields for a single webhook.

### `invalid_webhook_uuid`

The provided webhook `uuid` is not a valid uuid v4 value.

## `io_error`

This error generally occurs when the host system has no space left on the device or when the database doesn't have read or write access.

## `index_primary_key_no_candidate_found`

[Primary key inference](/learn/getting_started/primary_key#meilisearch-guesses-your-primary-key) failed as the received documents do not contain any fields ending with `id`. [Manually designate the primary key](/learn/getting_started/primary_key#setting-the-primary-key), or add some field ending with `id` to your documents.

## `malformed_payload`

The [Content-Type header](/reference/api/overview#content-type) does not match the request body payload format or the format is invalid.

## `missing_api_key_actions`

The [`actions`](/reference/api/keys#actions) field is missing from payload.

## `missing_api_key_expires_at`

The [`expiresAt`](/reference/api/keys#expiresat) field is missing from payload.

## `missing_api_key_indexes`

The [`indexes`](/reference/api/keys#indexes) field is missing from payload.

## `missing_authorization_header`

This error happens if:

- The requested resources are protected with an API key that was not provided in the request header. Check our [security tutorial](/learn/security/basic_security) for more information
- You are using the wrong authorization header for your version. **v0.24 and below** use `X-MEILI-API-KEY: apiKey`, whereas **v0.25 and above** use `Authorization: Bearer apiKey`

## `missing_content_type`

The payload does not contain a [Content-Type header](/reference/api/overview#content-type). Currently, Meilisearch only supports JSON, CSV, and NDJSON.

## `missing_document_filter`

This payload is missing the [`filter`](/reference/api/documents#body-3) field.

## `missing_document_id`

A document does not contain any value for the required primary key, and is thus invalid. Check documents in the current addition for the invalid ones.

## `missing_index_uid`

The payload is missing the [`uid`](/reference/api/indexes#index-object) field.

## `missing_facet_search_facet_name`

The [`facetName`](/reference/api/facet_search#body) parameter is required.

## `missing_master_key`

You need to set a master key before you can access the `/keys` route. Read more about setting a master key at launch in our [security tutorial](/learn/security/basic_security).

## `missing_network_url`

One of the remotes in the [network object](/reference/api/network#the-network-object) does not contain the `url` field.

## `missing_payload`

The Content-Type header was specified, but no request body was sent to the server or the request body is empty.

## `missing_swap_indexes`

The index swap payload is missing the [`indexes`](/reference/api/indexes#swap-indexes) object.

## `missing_task_filters`

The [cancel tasks](/reference/api/tasks#cancel-tasks) and [delete tasks](/reference/api/tasks#delete-tasks) endpoints require one of the available query parameters.

## `no_space_left_on_device`

This error occurs if:

- The host system partition reaches its maximum capacity and can no longer accept writes
- The tasks queue reaches its limit and can no longer accept writes. You can delete tasks using the [delete tasks endpoint](/reference/api/tasks#delete-tasks) to continue write operations

## `not_found`

The requested resources could not be found.

## `payload_too_large`

The payload sent to the server was too large. Check out this [guide](/learn/self_hosted/configure_meilisearch_at_launch#payload-limit-size) to customize the maximum payload size accepted by Meilisearch.

## `task_not_found`

The requested task does not exist. Please ensure that you are using the correct [`uid`](/reference/api/tasks#uid).

## `too_many_open_files`

Indexing a large batch of documents, such as a JSON file over 3.5GB in size, can result in Meilisearch opening too many file descriptors. Depending on your machine, this might reach your system's default resource usage limits and trigger the `too_many_open_files` error. Use [`ulimit`](https://www.ibm.com/docs/en/aix/7.1?topic=u-ulimit-command) or a similar tool to increase resource consumption limits before running Meilisearch. e.g., call `ulimit -Sn 3000` in a UNIX environment to raise the number of allowed open file descriptors to 3000.

## `too_many_search_requests`

You have reached the limit of concurrent search requests. You may configure it by relaunching your instance and setting a higher value to [`--experimental-search-queue-size`](/learn/self_hosted/configure_meilisearch_at_launch).

## `unretrievable_document`

The document exists in store, but there was an error retrieving it. This probably comes from an inconsistent state in the database.

## `vector_embedding_error`

Error while generating embeddings. You may often see this error when the embedding provider service is currently unavailable. Most providers offer status pages to monitor the state of their services, such as OpenAI's https://status.openai.com/.

Inaccessible embedding provider errors usually include a message stating Meilisearch "could not reach embedding server".

## Remote federated search errors

### `remote_bad_response`

The remote instance answered with a response that this instance could not use as a federated search response.

### `remote_bad_request`

The remote instance answered with `400 BAD REQUEST`.

### `remote_could_not_send_request`

There was an error while sending the remote federated search request.

### `remote_invalid_api_key`

The remote instance answered with `403 FORBIDDEN` or `401 UNAUTHORIZED` to this instance’s request. The configured search API key is either missing, invalid, or lacks the required search permission.

### `remote_remote_error`

The remote instance answered with `500 INTERNAL ERROR`.

### `remote_timeout`

The proxy did not answer in the allocated time.

### `webhook_not_found`

The provided webhook `uuid` does not correspond to any configured webhooks in the instance.

---

## Errors

Meilisearch uses the following standard HTTP codes for a successful or failed API request: | Status code | Description | | :--- | :--- | | 200 | ✅ **Ok** Everything worked as expected. | | 201 | ✅ **Created** The resource has been created (synchronous) | | 202 | ✅ **Accepted** The task has been added to the queue (asynchronous) | | 204 | ✅ **No Content** The resource has been deleted or no content has been returned | | 205 | ✅ **Reset Content** All the resources have been deleted | | 400 | ❌ **Bad Request** The request was unacceptable, often due to missing a required parameter | | 401 | ❌ **Unauthorized** No valid API key provided | | 403 | ❌ **Forbidden** The API key doesn't have the permissions to perform the request | | 404 | ❌ **Not Found** The requested resource doesn't exist | ## Errors

All detailed task responses contain an [`error`](/reference/api/tasks#error) field. When a task fails, it is always accompanied by a JSON-formatted error response. Meilisearch errors can be of one of the following types: | Type | Description | | :--- | :--- | | **`invalid_request`** | This is due to an error in the user input. It is accompanied by the HTTP code `4xx` | | **`internal`** | This is due to machine or configuration constraints. It is accompanied by the HTTP code `5xx` | | **`auth`** | This type of error is related to authentication and authorization. It is accompanied by the HTTP code `4xx` | | **`system`** | This indicates your system has reached or exceeded its limit for disk size, index size, open files, or the database doesn't have read or write access. It is accompanied by the HTTP code `5xx` | ### Error format

```json
{
 "message": "Index `movies` not found.",
 "code": "index_not_found",
 "type": "invalid_request",
 "link": "https://docs.meilisearch.com/errors#index_not_found"
}
``` | Field | Description | | :--- | :--- | | **`message`** | Human-readable description of the error | | **`code`** | [Error code](/reference/errors/error_codes) | | **`type`** | [Type](#errors) of error returned | | **`link`** | Link to the relevant section of the documentation | If you're having trouble understanding an error, take a look at the [complete list](/reference/errors/error_codes) of `code` values and descriptions.

TEST RESPONSE FIELD COMPONENT

 Human-readable description of the error

 [Error code](/reference/errors/error_codes)

 [Type](#errors) of error returned

 Link to the relevant section of the documentation

---

# Guides & Tutorials

## Meilisearch & Model Context Protocol - Talk to Meilisearch with Claude desktop

# Model Context Protocol - Talk to Meilisearch with Claude desktop

## Introduction

This guide will walk you through setting up and using Meilisearch through natural language interactions with Claude AI via Model Context Protocol (MCP).

## Requirements

To follow this guide, you'll need:

- [Claude Desktop](https://claude.ai/download) (free)
- [A Cloud project](https://www.meilisearch.com/cloud) (14 days free-trial)
- Python ≥ 3.9
- From the Cloud dashboard, your Meilisearch host & api key

## Setting up Claude Desktop with the Meilisearch MCP Server

### 1. Install Claude Desktop

Download and install [Claude Desktop](https://claude.ai/download).

### 2. Install the Meilisearch MCP Server

You can install the Meilisearch MCP server using `uv` or `pip`:

```bash
# Using uv (recommended)
uv pip install meilisearch-mcp

# Using pip
pip install meilisearch-mcp
```

### 3. Configure Claude Desktop

Open Claude Desktop, click on the Claude menu in the top bar, and select "Settings". In the Settings window, click on "Developer" in the left sidebar, then click "Edit Config". This will open your `claude_desktop_config.json` file.

Add the Meilisearch MCP server to your configuration:

```json
{
 "mcpServers": {
 "meilisearch": {
 "command": "uvx",
 "args": ["-n", "meilisearch-mcp"]
 }
 }
```

Save the file and restart Claude.

## Connecting to Your Meilisearch Instance

Once Claude Desktop is set up with the Meilisearch MCP server, you can connect to your Meilisearch instance by asking Claude to update the connection settings.

Open Claude Desktop and start a new conversation.

Next, connect to your Meilisearch instance by asking Claude to update the connection settings, replacing `MEILISEARCH_URL` with your project URL and `API_KEY` with your project's API key:

```
Please connect to my Meilisearch instance at MEILISEARCH_URL using the API key API_KEY
```

Claude will use the MCP server's `update-connection-settings` tool to establish a connection to your Meilisearch instance.

Finally, verify the connection by asking:

```
Can you check the connection to my Meilisearch instance and tell me what version it's running?
```

Claude will use the `get-version` and `health-check` tools to verify the connection and provide information about your instance.

## Create an e-commerce index

Now you have configured the MCP to work with Meilisearch, you can use it to manage your indexes.

First, verify what indexes you have in your project:

```
What indexes do I have in my Meilisearch instance?
```

Next, ask Claude to create an index optimized for e-commerce:

```
Create a new index called "products" for our e-commerce site with the primary key "product_id"
```

Finally, check the index has been created successfully and is completely empty:

```
How many documents are in my "products" index and what's its size?
```

## Add documents to your new index

Ask Calude to add a couple of test documents to your "products" index:

```
Add these products to my "products" index:
[
 {"product_id": 1, "name": "Ergonomic Chair", "description": "Comfortable office chair", "price": 299.99, "category": "Furniture"},
 {"product_id": 2, "name": "Standing Desk", "description": "Adjustable height desk", "price": 499.99, "category": "Furniture"}
]
```

Since you are only using "products" for testing, you can also ask Claude to automatically populate it with placeholder data:

```
Add 10 documents in the index "products" with a name, category, price, and description of your choice
```

To verify data insertion worked as expected, retrieve the first few documents in your index:

```
Show me the first 5 products in my "products" index
```

## Configure your index

Before performing your first search, set a few index settings to ensure relevant results.

Ask Claude to prioritize exact word matches over multiple partial matches:

```
Update the ranking rules for the "products" index to prioritize word matches and handle typos, but make exact matches more important than proximity
```

It's also a good practice to limit searchable attributes only to highly-relevant fields, and only return attributes you are going to display in your search interface:

```
Configure my "products" index to make the "name" and "description" fields searchable, but only "name", "price", and "category" should be displayed in results
```

## Perform searches with MCP

Perform your first search with the following prompt:

```
Search the "products" index for "desk" and return the top 3 results
```

You can also request your search uses other Meilisearch features such as filters and sorting:

```
Search the "products" index for "chair" where the price is less than 200 and the category is "Furniture". Sort results by price in ascending order.
```

### Important note about LLM limitation

Large Language Models like Claude tend to say "yes" to most requests, even if they can't actually perform them.

Claude can only perform actions that are exposed through the Meilisearch API and implemented in the MCP server. If you're unsure whether a particular operation is possible, refer to the [Meilisearch documentation](https://docs.meilisearch.com) and the [MCP server README](https://github.com/meilisearch/meilisearch-mcp).

## Troubleshooting

If you encounter issues with the Meilisearch MCP integration, try these steps

### 1. Ask Claude to verify your connection settings

```
What are the current Meilisearch connection settings?
```

### 2. Ask Claude to check your Meilisearch instance health

```
Run a health check on my Meilisearch instance
```

### 3. Review Claude's logs

Open the logs file in your text editor or log viewer:

- On macOS: `~/Library/Logs/Claude/mcp*.log`
- On Windows: `%APPDATA%\Claude\logs\mcp*.log`

### 4. Test the MCP server independently

Open your terminal and query the MCP Inspector with `npx`:

```bash
npx @modelcontextprotocol/inspector uvx -n meilisearch-mcp
```

## Conclusion

The Meilisearch MCP integration with Claude can transform multiple API calls and configuration tasks into conversational requests. This can help you focus more on building your application and less on implementation details.

For more information about advanced configurations and capabilities, refer to the [Meilisearch documentation](https://docs.meilisearch.com) and the [Meilisearch MCP server repository](https://github.com/meilisearch/meilisearch-mcp).

---

## Computing Hugging Face embeddings with the GPU

This guide is aimed at experienced users working with a self-hosted Meilisearch instance. It shows you how to compile a Meilisearch binary that generates Hugging Face embeddings with an Nvidia GPU.

## Prerequisites

- A [CUDA-compatible Linux distribution](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html#id12)
- An Nvidia GPU with CUDA support
- A modern Rust compiler

## Install CUDA

Follow Nvidia's [CUDA installation instructions](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html).

## Verify your CUDA install

After you have installed CUDA in your machine, run the following command in your command-line terminal:

```sh
nvcc --version | head -1
```

If CUDA is working correctly, you will see the following response:

```
nvcc: NVIDIA (R) Cuda compiler driver
```

## Compile Meilisearch First, clone Meilisearch:

```sh
git clone https://github.com/meilisearch/meilisearch.git
```

Then, compile the Meilisearch binary with `cuda` enabled:

```sh
cargo build --release --features cuda
```

This might take a few moments. Once the compiler is done, you should have a CUDA-compatible Meilisearch binary.

## Configure the Hugging Face embedder

Run your freshly compiled binary:

```sh
./Meilisearch ```

Then add the Hugging Face embedder to your index settings:

```sh
curl \
 -X PATCH 'MEILISEARCH_URL/indexes/INDEX_NAME/settings/embedders' \
 -H 'Content-Type: application/json' \
 --data-binary '{ "default": { "source": "huggingFace" } }'
```

Meilisearch will return a summarized task object and place your request on the task queue:

```json
{
 "taskUid": 1,
 "indexUid": "INDEX_NAME",
 "status": "enqueued",
 "type": "settingsUpdate",
 "enqueuedAt": "2024-03-04T15:05:43.383955Z"
}
```

Use the task object's `taskUid` to [monitor the task status](/reference/api/tasks#get-one-task). The Hugging Face embedder will be ready to use once the task is completed.

## Conclusion

You have seen how to compile a Meilisearch binary that uses your Nvidia GPU to compute vector embeddings. Doing this should significantly speed up indexing when using Hugging Face.

---

## Using Meilisearch with Docker

In this guide you will learn how to use Docker to download and run Meilisearch, configure its behavior, and manage your Meilisearch data.

Docker is a tool that bundles applications into containers. Docker containers ensure your application runs the same way in different environments. When using Docker for development, we recommend following [the official instructions to install Docker Desktop](https://docs.docker.com/get-docker/).

## Download Meilisearch with Docker

Docker containers are distributed in images. To use Meilisearch, use the `docker pull` command to download a Meilisearch image:

```sh
docker pull getmeili/meilisearch:v1.16
```

Meilisearch deploys a new Docker image with every release of the engine. Each image is tagged with the corresponding Meilisearch version, indicated in the above example by the text following the `:` symbol. You can see [the full list of available Meilisearch Docker images](https://hub.docker.com/r/getmeili/meilisearch/tags#!) on Docker Hub.

The `latest` tag will always download the most recent Meilisearch release. Meilisearch advises against using it, as it might result in different machines running different images if significant time passes between setting up each one of them.

## Run Meilisearch with Docker

After completing the previous step, use `docker run` to launch the Meilisearch image:

```sh
docker run -it --rm \
 -p 7700:7700 \
 -v $(pwd)/meili_data:/meili_data \
 getmeili/meilisearch:v1.16
```

### Configure Meilisearch Meilisearch accepts a number of instance options during launch. You can configure these in two ways: environment variables and CLI arguments. Note that some options are only available as CLI arguments—[consult our configuration reference for more details](/learn/self_hosted/configure_meilisearch_at_launch).

#### Passing instance options with environment variables

To pass environment variables to Docker, add the `-e` argument to `docker run`. The example below launches Meilisearch with a master key:

```sh
docker run -it --rm \
 -p 7700:7700 \
 -e MEILI_MASTER_KEY='MASTER_KEY'\
 -v $(pwd)/meili_data:/meili_data \
 getmeili/meilisearch:v1.16
```

#### Passing instance options with CLI arguments

If you want to pass command-line arguments to Meilisearch with Docker, you must add a line to the end of your `docker run` command explicitly launching the `meilisearch` binary:

```sh
docker run -it --rm \
 -p 7700:7700 \
 -v $(pwd)/meili_data:/meili_data \
 getmeili/meilisearch:v1.16 \
 Meilisearch --master-key="MASTER_KEY"
```

## Managing data

When using Docker, your working directory is `/meili_data`. This means the location of your database file is `/meili_data/data.ms`.

### Data persistency

By default, data written to a Docker container is deleted every time the container stops running. This data includes your indexes and the documents they store.

To keep your data intact between reboots, specify a dedicated volume by running Docker with the `-v` command-line option:

```sh
docker run -it --rm \
 -p 7700:7700 \
 -v $(pwd)/meili_data:/meili_data \
 getmeili/meilisearch:v1.16
```

The example above uses `$(pwd)/meili_data`, which is a directory in the host machine. Depending on your OS, mounting volumes from the host to the container might result in performance loss and is only recommended when developing your application.

### Generating dumps and updating Meilisearch To export a dump, [use the create dump endpoint as described in our dumps guide](/learn/data_backup/dumps). Once the task is complete, you can access the dump file in `/meili_data/dumps` inside the volume you passed with `-v`.

To import a dump, use Meilisearch's `--import-dump` command-line option and specify the path to the dump file. Make sure the path points to a volume reachable by Docker:

```sh
docker run -it --rm \
 -p 7700:7700 \
 -v $(pwd)/meili_data:/meili_data \
 getmeili/meilisearch:v1.16 \
 Meilisearch --import-dump /meili_data/dumps/20200813-042312213.dump
```

Note that exporting and importing dumps require using command-line arguments. [For more information on how to run Meilisearch with CLI options and Docker, refer to this guide's relevant section.](#passing-instance-options-with-cli-arguments)

If you are storing your data in a persistent volume as instructed in [the data persistency section](#data-persistency), you must delete `/meili_data/data.ms` in that volume before importing a dump.

Use dumps to migrate data between different Meilisearch releases. [Read more about updating Meilisearch in our dedicated guide.](/learn/update_and_migration/updating)

### Snapshots

To generate a Meilisearch snapshot with Docker, launch Meilisearch with `--schedule-snapshot` and `--snapshot-dir`:

```sh
docker run -it --rm \
 -p 7700:7700 \
 -v $(pwd)/meili_data:/meili_data \
 getmeili/meilisearch:v1.16 \
 Meilisearch --schedule-snapshot --snapshot-dir /meili_data/snapshots
```

`--snapshot-dir` should point to a folder inside the Docker working directory for Meilisearch, `/meili_data`. Once generated, snapshots will be available in the configured directory.

To import a snapshot, launch Meilisearch with the `--import-snapshot` option:

```sh
docker run -it --rm \
 -p 7700:7700 \
 -v $(pwd)/meili_data:/meili_data \
 getmeili/meilisearch:v1.16 \
 Meilisearch --import-snapshot /meili_data/snapshots/data.ms.snapshot
```

Use snapshots for backup or when migrating data between two Meilisearch instances of the same version. [Read more about snapshots in our guide.](/learn/data_backup/snapshots)

---

## Semantic Search with Cloudflare Worker AI Embeddings

## Introduction

This guide will walk you through the process of setting up Meilisearch with Cloudflare Worker AI embeddings to enable semantic search capabilities. By leveraging Meilisearch's AI features and Cloudflare Worker AI's embedding API, you can enhance your search experience and retrieve more relevant results.

## Requirements

To follow this guide, you'll need:

- A [Cloud](https://www.meilisearch.com/cloud) project running version >=1.13
- A Cloudflare account with access to Worker AI and an API key. You can sign up for a Cloudflare account at [Cloudflare](https://www.cloudflare.com/)
- Your Cloudflare account ID

## Setting up Meilisearch To set up an embedder in Meilisearch, you need to configure it to your settings. You can refer to the [Meilisearch documentation](/reference/api/settings) for more details on updating the embedder settings.

Cloudflare Worker AI offers the following embedding models:

- `baai/bge-base-en-v1.5`: 768 dimensions
- `baai/bge-large-en-v1.5`: 1024 dimensions
- `baai/bge-small-en-v1.5`: 384 dimensions

Here's an example of embedder settings for Cloudflare Worker AI:

```json
{
 "cloudflare": {
 "source": "rest",
 "apiKey": "<API Key>",
 "dimensions": 384,
 "documentTemplate": "<Custom template (Optional, but recommended)>",
 "url": "https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/run/@cf/",
 "request": {
 "text": ["{{text}}", "{{..}}"]
 },
 "response": {
 "result": {
 "data": ["{{embedding}}", "{{..}}"]
 }
 }
 }
}
```

In this configuration:

- `source`: Specifies the source of the embedder, which is set to "rest" for using a REST API.
- `apiKey`: Replace `<API Key>` with your actual Cloudflare API key.
- `dimensions`: Specifies the dimensions of the embeddings. Set to 384 for `baai/bge-small-en-v1.5`, 768 for `baai/bge-base-en-v1.5`, or 1024 for `baai/bge-large-en-v1.5`.
- `documentTemplate`: Optionally, you can provide a [custom template](/learn/ai_powered_search/getting_started_with_ai_search) for generating embeddings from your documents.
- `url`: Specifies the URL of the Cloudflare Worker AI API endpoint.
- `request`: Defines the request structure for the Cloudflare Worker AI API, including the input parameters.
- `response`: Defines the expected response structure from the Cloudflare Worker AI API, including the embedding data.

Be careful when setting up the `url` field in your configuration. The URL contains your Cloudflare account ID (`<ACCOUNT_ID>`) and the specific model you want to use (``). Make sure to replace these placeholders with your actual account ID and the desired model name (e.g., `baai/bge-small-en-v1.5`).

Once you've configured the embedder settings, Meilisearch will automatically generate embeddings for your documents and store them in the vector store.

note: Cloudflare may have rate limiting, which is managed by Meilisearch. If you have a free account, the indexation process may take some time, but Meilisearch will handle it with a retry strategy.

It's recommended to monitor the tasks queue to ensure everything is running smoothly. You can access the tasks queue using the Cloud UI or the [Meilisearch API](/reference/api/tasks).

## Testing semantic search

With the embedder set up, you can now perform semantic searches using Meilisearch. When you send a search query, Meilisearch will generate an embedding for the query using the configured embedder and then use it to find the most semantically similar documents in the vector store.
To perform a semantic search, you simply need to make a normal search request but include the hybrid parameter:

```json
{
 "q": "<Query made by the user>",
 "hybrid": {
 "semanticRatio": 1,
 "embedder": "cloudflare"
 }
}
```

In this request:

- `q`: Represents the user's search query.
- `hybrid`: Specifies the configuration for the hybrid search.
 - `semanticRatio`: Allows you to control the balance between semantic search and traditional search. A value of 1 indicates pure semantic search, while a value of 0 represents full-text search. You can adjust this parameter to achieve a hybrid search experience.
 - `embedder`: The name of the embedder used for generating embeddings. Make sure to use the same name as specified in the embedder configuration, which in this case is "cloudflare".

You can use the Meilisearch API or client libraries to perform searches and retrieve the relevant documents based on semantic similarity.

## Conclusion

By following this guide, you should now have Meilisearch set up with Cloudflare Worker AI embedding, enabling you to leverage semantic search capabilities in your application. Meilisearch's auto-batching and efficient handling of embeddings make it a powerful choice for integrating semantic search into your project.

To explore further configuration options for embedders, consult the [detailed documentation about the embedder setting possibilities](/reference/api/settings).

---

## Semantic Search with Cohere Embeddings

## Introduction

This guide will walk you through the process of setting up Meilisearch with Cohere embeddings to enable semantic search capabilities. By leveraging Meilisearch's AI features and Cohere's embedding API, you can enhance your search experience and retrieve more relevant results.

## Requirements

To follow this guide, you'll need:

- A [Cloud](https://www.meilisearch.com/cloud) project running version >=1.13
- A Cohere account with an API key for embedding generation. You can sign up for a Cohere account at [Cohere](https://cohere.com/).
- No backend required.

## Setting up Meilisearch To set up an embedder in Meilisearch, you need to configure it to your settings. You can refer to the [Meilisearch documentation](/reference/api/settings) for more details on updating the embedder settings.

Cohere offers multiple embedding models:

- `embed-english-v3.0` and `embed-multilingual-v3.0`: 1024 dimensions
- `embed-english-light-v3.0` and `embed-multilingual-light-v3.0`: 384 dimensions

Here's an example of embedder settings for Cohere:

```json
{
 "cohere": {
 "source": "rest",
 "apiKey": "<Cohere API Key>",
 "dimensions": 1024,
 "documentTemplate": "<Custom template (Optional, but recommended)>",
 "url": "https://api.cohere.com/v1/embed",
 "request": {
 "model": "embed-english-v3.0",
 "texts": [
 "{{text}}",
 "{{..}}"
 ],
 "input_type": "search_document"
 },
 "response": {
 "embeddings": [
 "{{embedding}}",
 "{{..}}"
 ]
 },
 }
}
```

In this configuration:

- `source`: Specifies the source of the embedder, which is set to "rest" for using a REST API.
- `apiKey`: Replace `<Cohere API Key>` with your actual Cohere API key.
- `dimensions`: Specifies the dimensions of the embeddings, set to 1024 for the `embed-english-v3.0` model.
- `documentTemplate`: Optionally, you can provide a [custom template](/learn/ai_powered_search/getting_started_with_ai_search) for generating embeddings from your documents.
- `url`: Specifies the URL of the Cohere API endpoint.
- `request`: Defines the request structure for the Cohere API, including the model name and input parameters.
- `response`: Defines the expected response structure from the Cohere API, including the embedding data.

Once you've configured the embedder settings, Meilisearch will automatically generate embeddings for your documents and store them in the vector store.

note: most third-party tools have rate limiting, which is managed by Meilisearch. If you have a free account, the indexation process may take some time, but Meilisearch will handle it with a retry strategy.

It's recommended to monitor the tasks queue to ensure everything is running smoothly. You can access the tasks queue using the Cloud UI or the [Meilisearch API](https://www.meilisearch.com/docs/reference/api/tasks).

## Testing semantic search

With the embedder set up, you can now perform semantic searches using Meilisearch. When you send a search query, Meilisearch will generate an embedding for the query using the configured embedder and then use it to find the most semantically similar documents in the vector store.
To perform a semantic search, you simply need to make a normal search request but include the hybrid parameter:

```json
{
 "q": "<Query made by the user>",
 "hybrid": {
 "semanticRatio": 1,
 "embedder": "cohere"
 }
}
```

In this request:

- `q`: Represents the user's search query.
- `hybrid`: Specifies the configuration for the hybrid search.
 - `semanticRatio`: Allows you to control the balance between semantic search and traditional search. A value of 1 indicates pure semantic search, while a value of 0 represents full-text search. You can adjust this parameter to achieve a hybrid search experience.
 - `embedder`: The name of the embedder used for generating embeddings. Make sure to use the same name as specified in the embedder configuration, which in this case is "cohere".

You can use the Meilisearch API or client libraries to perform searches and retrieve the relevant documents based on semantic similarity.

## Conclusion

By following this guide, you should now have Meilisearch set up with Cohere embedding, enabling you to leverage semantic search capabilities in your application. Meilisearch's auto-batching and efficient handling of embeddings make it a powerful choice for integrating semantic search into your project.

To explore further configuration options for embedders, consult the [detailed documentation about the embedder setting possibilities](/reference/api/settings).

---

## Semantic Search with Gemini Embeddings

## Requirements

To follow this guide, you'll need:

- A [Cloud](https://www.meilisearch.com/cloud) project running version >=1.13
- A Google account with an API key for embedding generation. You can sign up for a Google account at [Google](https://google.com/)

## Setting up Meilisearch To set up an embedder in Meilisearch, you need to configure it to your settings. You can refer to the [Meilisearch documentation](/reference/api/settings) for more details on updating the embedder settings.

While using Gemini to generate embeddings, you'll need to use the model `gemini-embedding-001`. Unlike some other services, Gemini currently offers only one embedding model.

Here's an example of embedder settings for Gemini:

```json
{
 "gemini": {
 "source": "rest",
 "dimensions": 3072,
 "documentTemplate": "<Custom template (Optional, but recommended)>",
 "headers": {
 "Content-Type": "application/json",
 "x-goog-api-key": "<Google API Key>"
 },
 "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents",
 "request": {
 "requests": [
 {
 "model": "models/gemini-embedding-001",
 "content": {
 "parts": [
 { "text": "{{text}}" }
 ]
 }
 },
 "{{..}}"
 ]
 },
 "response": {
 "embeddings": [
 { "values": "{{embedding}}" },
 "{{..}}"
 ]
 }
 }
}
 ```

In this configuration:

- `source`: Specifies the source of the embedder, which is set to "rest" for using a REST API.
- `headers`: Replace `<Google API Key>` with your actual Google API key.
- `dimensions`: Specifies the dimensions of the embeddings, set to 3072 for the `gemini-embedding-001` model.
- `documentTemplate`: Optionally, you can provide a [custom template](/learn/ai_powered_search/getting_started_with_ai_search) for generating embeddings from your documents.
- `url`: Specifies the URL of the Gemini API endpoint.
- `request`: Defines the request structure for the Gemini API, including the model name and input parameters.
- `response`: Defines the expected response structure from the Gemini API, including the embedding data.

Once you've configured the embedder settings, Meilisearch will automatically generate embeddings for your documents and store them in the vector store.

note: most third-party tools have rate limiting, which is managed by Meilisearch. If you have a free account, the indexation process may take some time, but Meilisearch will handle it with a retry strategy.

It's recommended to monitor the tasks queue to ensure everything is running smoothly. You can access the tasks queue using the Cloud UI or the [Meilisearch API](https://www.meilisearch.com/docs/reference/api/tasks).

## Testing semantic search

With the embedder set up, you can now perform semantic searches using Meilisearch. When you send a search query, Meilisearch will generate an embedding for the query using the configured embedder and then use it to find the most semantically similar documents in the vector store.
To perform a semantic search, you simply need to make a normal search request but include the hybrid parameter:

```json
{
 "q": "<Query made by the user>",
 "hybrid": {
 "semanticRatio": 1,
 "embedder": "gemini"
 }
}
```

In this request:

- `q`: Represents the user's search query.
- `hybrid`: Specifies the configuration for the hybrid search.
 - `semanticRatio`: Allows you to control the balance between semantic search and traditional search. A value of 1 indicates pure semantic search, while a value of 0 represents full-text search. You can adjust this parameter to achieve a hybrid search experience.
 - `embedder`: The name of the embedder used for generating embeddings. Make sure to use the same name as specified in the embedder configuration, which in this case is "gemini".

You can use the Meilisearch API or client libraries to perform searches and retrieve the relevant documents based on semantic similarity.

## Conclusion

By following this guide, you should now have Meilisearch set up with Gemini embedding, enabling you to leverage semantic search capabilities in your application. Meilisearch's auto-batching and efficient handling of embeddings make it a powerful choice for integrating semantic search into your project.

To explore further configuration options for embedders, consult the [detailed documentation about the embedder setting possibilities](/reference/api/settings).

---

## Semantic Search with Hugging Face Inference Endpoints

## Introduction

This guide will walk you through the process of setting up a Meilisearch REST embedder with [Hugging Face Inference Endpoints](https://ui.endpoints.huggingface.co/) to enable semantic search capabilities.

You can use Hugging Face and Meilisearch in two ways: running the model locally by setting the embedder source to `huggingface`, or remotely in Hugging Face's servers by setting the embeder source to `rest`.

## Requirements

To follow this guide, you'll need:

- A [Cloud](https://www.meilisearch.com/cloud) project running version >=1.13
- A [Hugging Face account](https://huggingface.co/) with a deployed inference endpoint
- The endpoint URL and API key of the deployed model on your Hugging Face account

## Configure the embedder

Set up an embedder using the update settings endpoint:

```json
{
 "hf-inference": {
 "source": "rest",
 "url": "ENDPOINT_URL",
 "apiKey": "API_KEY",
 "dimensions": 384,
 "documentTemplate": "CUSTOM_LIQUID_TEMPLATE",
 "request": {
 "inputs": ["{{text}}", "{{..}}"],
 "model": "baai/bge-small-en-v1.5"
 },
 "response": ["{{embedding}}", "{{..}}"]
 }
}
```

In this configuration:

- `source`: declares Meilisearch should connect to this embedder via its REST API
- `url`: replace `ENDPOINT_URL` with the address of your Hugging Face model endpoint
- `apiKey`: replace `API_KEY` with your Hugging Face API key
- `dimensions`: specifies the dimensions of the embeddings, which are 384 for `baai/bge-small-en-v1.5`
- `documentTemplate`: an optional but recommended [template](/learn/ai_powered_search/getting_started_with_ai_search) for the data you will send the embedder
- `request`: defines the structure and parameters of the request Meilisearch will send to the embedder
- `response`: defines the structure of the embedder's response

Once you've configured the embedder, Meilisearch will automatically generate embeddings for your documents. Monitor the task using the Cloud UI or the [get task endpoint](/reference/api/tasks).

This example uses [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) as its model, but Hugging Face offers [other options that may fit your dataset better](https://ui.endpoints.huggingface.co/catalog?task=sentence-embeddings).

## Perform a semantic search

With the embedder set up, you can now perform semantic searches. Make a search request with the `hybrid` search parameter, setting `semanticRatio` to `1`:

```json
{
 "q": "QUERY_TERMS",
 "hybrid": {
 "semanticRatio": 1,
 "embedder": "hf-inference"
 }
}
```

In this request:

- `q`: the search query
- `hybrid`: enables AI-powered search functionality
 - `semanticRatio`: controls the balance between semantic search and full-text search. Setting it to `1` means you will only receive semantic search results
 - `embedder`: the name of the embedder used for generating embeddings

## Conclusion

You have set up with an embedder using Hugging Face Inference Endpoints. This allows you to use pure semantic search capabilities in your application.

Consult the [embedder setting documentation](/reference/api/settings) for more information on other embedder configuration options.

---

## Semantic Search with Mistral Embeddings

## Introduction

This guide will walk you through the process of setting up Meilisearch with Mistral embeddings to enable semantic search capabilities. By leveraging Meilisearch's AI features and Mistral's embedding API, you can enhance your search experience and retrieve more relevant results.

## Requirements

To follow this guide, you'll need:

- A [Cloud](https://www.meilisearch.com/cloud) project running version >=1.13
- A Mistral account with an API key for embedding generation. You can sign up for a Mistral account at [Mistral](https://mistral.ai/).
- No backend required.

## Setting up Meilisearch To set up an embedder in Meilisearch, you need to configure it to your settings. You can refer to the [Meilisearch documentation](/reference/api/settings) for more details on updating the embedder settings.

While using Mistral to generate embeddings, you'll need to use the model `mistral-embed`. Unlike some other services, Mistral currently offers only one embedding model.

Here's an example of embedder settings for Mistral:

```json
{
 "mistral": {
 "source": "rest",
 "apiKey": "<Mistral API Key>",
 "dimensions": 1024,
 "documentTemplate": "<Custom template (Optional, but recommended)>",
 "url": "https://api.mistral.ai/v1/embeddings",
 "request": {
 "model": "mistral-embed",
 "input": ["{{text}}", "{{..}}"]
 },
 "response": {
 "data": [
 {
 "embedding": "{{embedding}}"
 },
 "{{..}}"
 ]
 }
 }
}
```

In this configuration:

- `source`: Specifies the source of the embedder, which is set to "rest" for using a REST API.
- `apiKey`: Replace `<Mistral API Key>` with your actual Mistral API key.
- `dimensions`: Specifies the dimensions of the embeddings, set to 1024 for the `mistral-embed` model.
- `documentTemplate`: Optionally, you can provide a [custom template](/learn/ai_powered_search/getting_started_with_ai_search) for generating embeddings from your documents.
- `url`: Specifies the URL of the Mistral API endpoint.
- `request`: Defines the request structure for the Mistral API, including the model name and input parameters.
- `response`: Defines the expected response structure from the Mistral API, including the embedding data.

Once you've configured the embedder settings, Meilisearch will automatically generate embeddings for your documents and store them in the vector store.

note: most third-party tools have rate limiting, which is managed by Meilisearch. If you have a free account, the indexation process may take some time, but Meilisearch will handle it with a retry strategy.

It's recommended to monitor the tasks queue to ensure everything is running smoothly. You can access the tasks queue using the Cloud UI or the [Meilisearch API](/reference/api/tasks)

## Testing semantic search

With the embedder set up, you can now perform semantic searches using Meilisearch. When you send a search query, Meilisearch will generate an embedding for the query using the configured embedder and then use it to find the most semantically similar documents in the vector store.
To perform a semantic search, you simply need to make a normal search request but include the hybrid parameter:

```json
{
 "q": "<Query made by the user>",
 "hybrid": {
 "semanticRatio": 1,
 "embedder": "mistral"
 }
}
```

In this request:

- `q`: Represents the user's search query.
- `hybrid`: Specifies the configuration for the hybrid search.
 - `semanticRatio`: Allows you to control the balance between semantic search and traditional search. A value of 1 indicates pure semantic search, while a value of 0 represents full-text search. You can adjust this parameter to achieve a hybrid search experience.
 - `embedder`: The name of the embedder used for generating embeddings. Make sure to use the same name as specified in the embedder configuration, which in this case is "mistral".

You can use the Meilisearch API or client libraries to perform searches and retrieve the relevant documents based on semantic similarity.

## Conclusion

By following this guide, you should now have Meilisearch set up with Mistral embedding, enabling you to leverage semantic search capabilities in your application. Meilisearch's auto-batching and efficient handling of embeddings make it a powerful choice for integrating semantic search into your project.

To explore further configuration options for embedders, consult the [detailed documentation about the embedder setting possibilities](/reference/api/settings).

---

## Semantic Search with OpenAI Embeddings

## Introduction

This guide will walk you through the process of setting up Meilisearch with OpenAI embeddings to enable semantic search capabilities. By leveraging Meilisearch's AI features and OpenAI's embedding API, you can enhance your search experience and retrieve more relevant results.

## Requirements

To follow this guide, you'll need:

- A [Cloud](https://www.meilisearch.com/cloud) project running version >=1.13
- An OpenAI account with an API key for embedding generation. You can sign up for an OpenAI account at [OpenAI](https://openai.com/).
- No backend required.

## Setting up Meilisearch To set up an embedder in Meilisearch, you need to configure it to your settings. You can refer to the [Meilisearch documentation](/reference/api/settings) for more details on updating the embedder settings.

OpenAI offers three main embedding models:

- `text-embedding-3-large`: 3,072 dimensions
- `text-embedding-3-small`: 1,536 dimensions
- `text-embedding-ada-002`: 1,536 dimensions

Here's an example of embedder settings for OpenAI:

```json
{
 "openai": {
 "source": "openAi",
 "apiKey": "<OpenAI API Key>",
 "dimensions": 1536,
 "documentTemplate": "<Custom template (Optional, but recommended)>",
 "model": "text-embedding-3-small"
 }
}
```

In this configuration:

- `source`: Specifies the source of the embedder, which is set to "openAi" for using OpenAI's API.
- `apiKey`: Replace `<OpenAI API Key>` with your actual OpenAI API key.
- `dimensions`: Specifies the dimensions of the embeddings. Set to 1536 for `text-embedding-3-small` and `text-embedding-ada-002`, or 3072 for `text-embedding-3-large`.
- `documentTemplate`: Optionally, you can provide a [custom template](/learn/ai_powered_search/getting_started_with_ai_search) for generating embeddings from your documents.
- `model`: Specifies the OpenAI model to use for generating embeddings. Choose from `text-embedding-3-large`, `text-embedding-3-small`, or `text-embedding-ada-002`.

Once you've configured the embedder settings, Meilisearch will automatically generate embeddings for your documents and store them in the vector store.

note: OpenAI has rate limiting, which is managed by Meilisearch. If you have a free account, the indexation process may take some time, but Meilisearch will handle it with a retry strategy.

It's recommended to monitor the tasks queue to ensure everything is running smoothly. You can access the tasks queue using the Cloud UI or the [Meilisearch API](/reference/api/tasks)

## Testing semantic search

With the embedder set up, you can now perform semantic searches using Meilisearch. When you send a search query, Meilisearch will generate an embedding for the query using the configured embedder and then use it to find the most semantically similar documents in the vector store.
To perform a semantic search, you simply need to make a normal search request but include the hybrid parameter:

```json
{
 "q": "<Query made by the user>",
 "hybrid": {
 "semanticRatio": 1,
 "embedder": "openai"
 }
}
```

In this request:

- `q`: Represents the user's search query.
- `hybrid`: Specifies the configuration for the hybrid search.
 - `semanticRatio`: Allows you to control the balance between semantic search and traditional search. A value of 1 indicates pure semantic search, while a value of 0 represents full-text search. You can adjust this parameter to achieve a hybrid search experience.
 - `embedder`: The name of the embedder used for generating embeddings. Make sure to use the same name as specified in the embedder configuration, which in this case is "openai".

You can use the Meilisearch API or client libraries to perform searches and retrieve the relevant documents based on semantic similarity.

## Conclusion

By following this guide, you should now have Meilisearch set up with OpenAI embedding, enabling you to leverage semantic search capabilities in your application. Meilisearch's auto-batching and efficient handling of embeddings make it a powerful choice for integrating semantic search into your project.

To explore further configuration options for embedders, consult the [detailed documentation about the embedder setting possibilities](/reference/api/settings).

---

## Semantic Search with Voyage AI Embeddings

## Introduction

This guide will walk you through the process of setting up Meilisearch with Voyage AI embeddings to enable semantic search capabilities. By leveraging Meilisearch's AI features and Voyage AI's embedding API, you can enhance your search experience and retrieve more relevant results.

## Requirements

To follow this guide, you'll need:

- A [Cloud](https://www.meilisearch.com/cloud) project running version >=1.13
- A Voyage AI account with an API key for embedding generation. You can sign up for a Voyage AI account at [Voyage AI](https://www.voyageai.com/).
- No backend required.

## Setting up Meilisearch To set up an embedder in Meilisearch, you need to configure it to your settings. You can refer to the [Meilisearch documentation](/reference/api/settings) for more details on updating the embedder settings.

Voyage AI offers the following embedding models:

- `voyage-large-2-instruct`: 1024 dimensions
- `voyage-multilingual-2`: 1024 dimensions
- `voyage-large-2`: 1536 dimensions
- `voyage-2`: 1024 dimensions

Here's an example of embedder settings for Voyage AI:

```json
{
 "voyage": {
 "source": "rest",
 "apiKey": "<Voyage AI API Key>",
 "dimensions": 1024,
 "documentTemplate": "<Custom template (Optional, but recommended)>",
 "url": "https://api.voyageai.com/v1/embeddings",
 "request": {
 "model": "voyage-2",
 "input": ["{{text}}", "{{..}}"]
 },
 "response": {
 "data": [
 {
 "embedding": "{{embedding}}"
 },
 "{{..}}"
 ]
 }
 }
}
```

In this configuration:

- `source`: Specifies the source of the embedder, which is set to "rest" for using a REST API.
- `apiKey`: Replace `<Voyage AI API Key>` with your actual Voyage AI API key.
- `dimensions`: Specifies the dimensions of the embeddings. Set to 1024 for `voyage-2`, `voyage-large-2-instruct`, and `voyage-multilingual-2`, or 1536 for `voyage-large-2`.
- `documentTemplate`: Optionally, you can provide a [custom template](/learn/ai_powered_search/getting_started_with_ai_search) for generating embeddings from your documents.
- `url`: Specifies the URL of the Voyage AI API endpoint.
- `request`: Defines the request structure for the Voyage AI API, including the model name and input parameters.
- `response`: Defines the expected response structure from the Voyage AI API, including the embedding data.

Once you've configured the embedder settings, Meilisearch will automatically generate embeddings for your documents and store them in the vector store.

note: most third-party tools have rate limiting, which is managed by Meilisearch. If you have a free account, the indexation process may take some time, but Meilisearch will handle it with a retry strategy.

It's recommended to monitor the tasks queue to ensure everything is running smoothly. You can access the tasks queue using the Cloud UI or the [Meilisearch API](/reference/api/tasks).

## Testing semantic search

With the embedder set up, you can now perform semantic searches using Meilisearch. When you send a search query, Meilisearch will generate an embedding for the query using the configured embedder and then use it to find the most semantically similar documents in the vector store.
To perform a semantic search, you simply need to make a normal search request but include the hybrid parameter:

```json
{
 "q": "<Query made by the user>",
 "hybrid": {
 "semanticRatio": 1,
 "embedder": "voyage"
 }
}
```

In this request:

- `q`: Represents the user's search query.
- `hybrid`: Specifies the configuration for the hybrid search.
 - `semanticRatio`: Allows you to control the balance between semantic search and traditional search. A value of 1 indicates pure semantic search, while a value of 0 represents full-text search. You can adjust this parameter to achieve a hybrid search experience.
 - `embedder`: The name of the embedder used for generating embeddings. Make sure to use the same name as specified in the embedder configuration, which in this case is "voyage".

You can use the Meilisearch API or client libraries to perform searches and retrieve the relevant documents based on semantic similarity.

## Conclusion

By following this guide, you should now have Meilisearch set up with Voyage AI embedding, enabling you to leverage semantic search capabilities in your application. Meilisearch's auto-batching and efficient handling of embeddings make it a powerful choice for integrating semantic search into your project.

To explore further configuration options for embedders, consult the [detailed documentation about the embedder setting possibilities](/reference/api/settings).

---

## Front-end integration

In the [quick start tutorial](/learn/self_hosted/getting_started_with_self_hosted_meilisearch), you learned how to launch Meilisearch and make a search request. This article will teach you how to create a simple front-end interface to search through your dataset.

Using [`instant-meilisearch`](https://github.com/meilisearch/instant-meilisearch) is the easiest way to build a front-end interface for search. `instant-meilisearch` is a plugin that establishes communication between a Meilisearch instance and [InstantSearch](https://github.com/algolia/instantsearch.js). InstantSearch, an open-source project developed by Algolia, renders all the components needed to start searching.

1. Create an empty file and name it `index.html`
2. Open it in a text editor like Notepad, Sublime Text, or Visual Studio Code
3. Copy-paste one the code sample below
4. Open `index.html` in your browser by double-clicking it in your folder

```js
<!DOCTYPE html>
<html lang="en">
 <head>
 <meta charset="utf-8" />
 <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@meilisearch/instant-meilisearch/templates/basic_search.css" />
 </head>
 <body>
 <div class="wrapper">
 <div id="searchbox" focus></div>
 <div id="hits"></div>
 </div>
 </body>
 <script src="https://cdn.jsdelivr.net/npm/@meilisearch/instant-meilisearch/dist/instant-meilisearch.umd.min.js"></script>
 <script src="https://cdn.jsdelivr.net/npm/instantsearch.js@4"></script>
 <script>
 const search = instantsearch({
 indexName: "movies",
 searchClient: instantMeiliSearch(
 "http://localhost:7700"
 ).searchClient
 });
 search.addWidgets([
 instantsearch.widgets.searchBox({
 container: "#searchbox"
 }),
 instantsearch.widgets.configure({ hitsPerPage: 8 }),
 instantsearch.widgets.hits({
 container: "#hits",
 templates: {
 item: `
 <div>
 <div class="hit-name">
 {{#helpers.highlight}}{ "attribute": "title" }{{/helpers.highlight}}
 </div>
 </div>
 `
 }
 })
 ]);
 search.start();
 </script>
</html>
```

Here's what's happening:

- The first four lines of the `<body>` add two container elements: `#searchbox` and `#hits`. `instant-meilisearch` creates the search bar inside `#searchbox` and lists search results in `#hits`
- The first two`<script src="…">` tags import libraries needed to run `instant-meilisearch`
- The third and final `<script>` tag is where you customize `instant-meilisearch`

You should now have a working front-end search interface. [Consult `instant-meilisearch`'s documentation for more information on how to further customize your search interface.](https://github.com/meilisearch/instant-meilisearch)

---

## Search result pagination

In a perfect world, users would not need to look beyond the first search result to find what they were looking for. In practice, however, it is usually necessary to create some kind of pagination interface to browse through long lists of results.

In this guide, we discuss two different approaches to pagination supported by Meilisearch: one using `offset` and `limit`, and another using `hitsPerPage` and `page`.

## Choosing the right pagination UI

There are many UI patterns that help your users navigate through search results. One common and efficient solution in Meilisearch is using `offset` and `limit` to create interfaces centered around ["Previous" and "Next" buttons](#previous-and-next-buttons).

Other solutions, such as [creating a page selector](/guides/front_end/pagination#numbered-page-selectors) allowing users to jump to any search results page, make use of `hitsPerPage` and `page` to obtain the exhaustive total number of matched documents. These tend to be less efficient and may result in decreased performance.

Whatever UI pattern you choose, there is a limited maximum number of search results Meilisearch will return for any given query. You can use [the `maxTotalHits` index setting](/reference/api/settings#pagination) to configure this, but be aware that higher limits will negatively impact search performance.

Setting `maxTotalHits` to a value higher than the default will negatively impact search performance. Setting `maxTotalHits` to values over `20000` may result in queries taking seconds to complete.

## "Previous" and "Next" buttons

Using "Previous" and "Next" buttons for pagination means that users can easily navigate through results, but don't have the ability to jump to an arbitrary results page. This is Meilisearch's recommended solution when creating paginated interfaces.

Though this approach offers less precision than a full-blown page selector, it does not require knowing the exact number of search results. Since calculating the exhaustive number of documents matching a query is a resource-intensive process, interfaces like this might offer better performance.

### Implementation

To implement this interface in a website or application, we make our queries with the `limit` and `offset` search parameters. Response bodies will include an `estimatedTotalHits` field, containing a partial count of search results. This is Meilisearch's default behavior:

```json
{
 "hits": [
 …
 ],
 "query": "",
 "processingTimeMs": 15,
 "limit": 10,
 "offset": 0,
 "estimatedTotalHits": 471
}
```

#### `limit` and `offset`

"Previous" and "Next" buttons can be implemented using the [`limit`](/reference/api/search#limit) and [`offset`](/reference/api/search#offset) search parameters.

`limit` sets the size of a page. If you set `limit` to `10`, Meilisearch's response will contain a maximum of 10 search results. `offset` skips a number of search results. If you set `offset` to `20`, Meilisearch's response will skip the first 20 search results.

e.g., you can use Meilisearch's JavaScript SDK to get the first ten films in a movies database:

```js
const results = await index.search("tarkovsky", { limit: 10, offset: 0 });
```

You can use both parameters together to create search pages.

#### Search pages and calculating `offset`

If you set `limit` to `20` and `offset` to `0`, you get the first twenty search results. We can call this our first page.

```js
const results = await index.search("tarkovsky", { limit: 20, offset: 0 });
```

Likewise, if you set `limit` to `20` and `offset` to `40`, you skip the first 40 search results and get documents ranked from 40 through 59. We can call this the third results page.

```js
const results = await index.search("tarkovsky", { limit: 20, offset: 40 });
```

You can use this formula to calculate a page's offset value: `offset = limit * (target page number - 1)`. In the previous example, the calculation would look like this: `offset = 20 * (3 - 1)`. This gives us `40` as the result: `offset = 20 * 2 = 40`.

Once a query returns fewer `hits` than your configured `limit`, you have reached the last results page.

#### Keeping track of the current page number

Even though this UI pattern does not allow users to jump to a specific page, it is still useful to keep track of the current page number.

The following JavaScript snippet stores the page number in an HTML element, `.pagination`, and updates it every time the user moves to a different search results page:

```js
function updatePageNumber(elem) {
 const directionBtn = elem.id
 // Get the page number stored in the pagination element
 let pageNumber = parseInt(document.querySelector('.pagination').dataset.pageNumber)

 // Update page number
 if (directionBtn === 'previous_button') {
 pageNumber = pageNumber - 1
 } else if (directionBtn === 'next_button') {
 pageNumber = pageNumber + 1
 }

 // Store new page number in the pagination element
 document.querySelector('.pagination').dataset.pageNumber = pageNumber
}

// Add data to our HTML element stating the user is on the first page
document.querySelector('.pagination').dataset.pageNumber = 0
// Each time a user clicks on the previous or next buttons, update the page number
document.querySelector('#previous_button').onclick = function () { updatePageNumber(this) }
document.querySelector('#next_button').onclick = function () { updatePageNumber(this) }
```

#### Disabling navigation buttons for first and last pages

It is often helpful to disable navigation buttons when the user cannot move to the "Next" or "Previous" page.

The "Previous" button should be disabled whenever your `offset` is `0`, as this indicates your user is on the first results page.

To know when to disable the "Next" button, we recommend setting your query's `limit` to the number of results you wish to display per page plus one. That extra `hit` should not be shown to the user. Its purpose is to indicate that there is at least one more document to display on the next page.

The following JavaScript snippet runs checks whether we should disable a button every time the user navigates to another search results page:

```js
function updatePageNumber() {
 const pageNumber = parseInt(document.querySelector('.pagination').dataset.pageNumber)

 const offset = pageNumber * 20
 const results = await index.search('x', { limit: 21, offset })

 // If offset equals 0, we're on the first results page
 if (offset === 0 ) {
 document.querySelector('#previous_button').disabled = true;
 }

 // If offset is bigger than 0, we're not on the first results page
 if (offset > 0 ) {
 document.querySelector('#previous_button').disabled = false;
 }

 // If Meilisearch returns 20 items or fewer,
 // we are on the last page
 if (results.hits.length < 21 ) {
 document.querySelector('#next_button').disabled = true;
 }

 // If Meilisearch returns exactly 21 results
 // and our page can only show 20 items at a time,
 // we have at least one more page with one result in it
 if (results.hits.length === 21 ) {
 document.querySelector('#next_button').disabled = false;
 }
}

document.querySelector('#previous_button').onclick = function () { updatePageNumber(this) }
document.querySelector('#next_button').onclick = function () { updatePageNumber(this) }
```

## Numbered page selectors

This type of pagination consists of a numbered list of pages accompanied by "Next" and "Previous" buttons. This is a common UI pattern that offers users a significant amount of precision when navigating results.

Calculating the total amount of search results for a query is a resource-intensive process. **Numbered page selectors might lead to performance issues**, especially if you increase `maxTotalHits` above its default value.

### Implementation

By default, Meilisearch queries only return `estimatedTotalHits`. This value is likely to change as a user navigates search results and should not be used to create calculate the number of search result pages.

When your query contains either [`hitsPerPage`](/reference/api/search#number-of-results-per-page), [`page`](/reference/api/search#page), or both these search parameters, Meilisearch returns `totalHits` and `totalPages` instead of `estimatedTotalHits`. `totalHits` contains the exhaustive number of results for that query, and `totalPages` contains the exhaustive number of pages of search results for the same query:

```json
{
 "hits": [
 …
 ],
 "query": "",
 "processingTimeMs": 35,
 "hitsPerPage": 20,
 "page": 1,
 "totalPages": 4,
 "totalHits": 100
}
```

#### Search pages with `hitsPerPage` and `page`

`hitsPerPage` defines the maximum number of search results on a page.

Since `hitsPerPage` defines the number of results on a page, it has a direct effect on the total number of pages for a query. e.g., if a query returns 100 results, setting `hitsPerPage` to `25` means you will have four pages of search results. Settings `hitsPerPage` to `50`, instead, means you will have only two pages of search results.

The following example returns the first 25 search results for a query:

```js
const results = await index.search(
 "tarkovsky",
 {
 hitsPerPage: 25,
 }
);
```

To navigate through pages of search results, use the `page` search parameter. If you set `hitsPerPage` to `25` and your `totalPages` is `4`, `page` `1` contains documents from 1 to 25. Setting `page` to `2` instead returns documents from 26 to 50:

```js
const results = await index.search(
 "tarkovsky",
 {
 hitsPerPage: 25,
 page: 2
 }
);
```

`hitsPerPage` and `page` take precedence over `offset` and `limit`. If a query contains either `hitsPerPage` or `page`, any values passed to `offset` and `limit` are ignored.

#### Create a numbered page list

The `totalPages` field included in the response contains the exhaustive count of search result pages based on your query's `hitsPerPage`. Use this to create a numbered list of pages.

For ease of use, queries with `hitsPerPage` and `page` always return the current page number. This means you do not need to manually keep track of which page you are displaying.

In the following example, we create a list of page buttons dynamically and highlight the current page:

```js
const pageNavigation = document.querySelector('#page-navigation');
const listContainer = pageNavigation.querySelector('#page-list');
const results = await index.search(
 "tarkovsky",
 {
 hitsPerPage: 25,
 page: 1
 }
);

const totalPages = results.totalPages;
const currentPage = results.page;

for (let i = 0; i < totalPages; i += 1) {
 const listItem = document.createElement('li');
 const pageButton = document.createElement('button');

 pageButton.innerHTML = i;

 if (currentPage === i) {
 listItem.classList.add("current-page");
 }

 listItem.append(pageButton);
 listContainer.append(listItem);
}
```

#### Adding navigation buttons

Your users are likely to be more interested in the page immediately after or before the current search results page. Because of this, it is often helpful to add "Next" and "Previous" buttons to your page list.

In this example, we add these buttons as the first and last elements of our page navigation component:

```js
const pageNavigation = document.querySelector('#page-navigation');

const buttonNext = document.createElement('button');
buttonNext.innerHTML = 'Next';

const buttonPrevious = document.createElement('button');
buttonPrevious.innerHTML = 'Previous';

pageNavigation.prepend(buttonPrevious);
pageNavigation.append(buttonNext);
```

We can also disable them as required when on the first or last page of search results:

```js
buttonNext.disabled = results.page === results.totalPages;
buttonPrevious.disabled = results.page === 1;
```

---

## React quick start

Integrate a search-as-you-type experience into your React app.

## 1. Create a React application

Create your React application using a [Vite](https://vitejs.dev/) template:

```bash
npm create vite@latest my-app -- --template react
```

## 2. Install the library of search components

Navigate to your React app and install `react-instantsearch`, `@meilisearch/instant-meilisearch`, and `instantsearch.css`.

```bash
npm install react-instantsearch @meilisearch/instant-Meilisearch instantsearch.css
```

- [React InstantSearch](https://github.com/algolia/instantsearch/): front-end tools to customize your search environment
- [instant-meilisearch](https://github.com/meilisearch/meilisearch-js-plugins/tree/main/packages/instant-meilisearch): Meilisearch client to connect with React InstantSearch
- [instantsearch.css](https://github.com/algolia/instantsearch/tree/master/packages/instantsearch.css) (optional): CSS library to add basic styles to the search components

## 3. Initialize the search client

Use the following URL and API key to connect to a Meilisearch instance containing data from Steam video games.

```jsx
import React from 'react';
import { instantMeiliSearch } from '@meilisearch/instant-meilisearch';

const { searchClient } = instantMeiliSearch(
 'https://ms-adf78ae33284-106.lon.meilisearch.io',
 'a63da4928426f12639e19d62886f621130f3fa9ff3c7534c5d179f0f51c4f303'
);
```

## 4. Add the InstantSearch provider

`` is the root provider component for the InstantSearch library. It takes two props: the `searchClient` and the [index name](/learn/getting_started/indexes#index-uid).

```jsx
import React from 'react';
import { InstantSearch } from 'react-instantsearch';
import { instantMeiliSearch } from '@meilisearch/instant-meilisearch';

const { searchClient } = instantMeiliSearch(
 'https://ms-adf78ae33284-106.lon.meilisearch.io',
 'a63da4928426f12639e19d62886f621130f3fa9ff3c7534c5d179f0f51c4f303'
);

const App = () => (
 <InstantSearch
 indexName="steam-videogames"
 >
 
);

export default App
```

## 5. Add a search bar and list search results

Add the `SearchBox` and `InfiniteHits` components inside the `InstantSearch` wrapper component. The Hits component accepts a custom Hit component via the `hitComponent` prop, which allows customizing how each search result is rendered.

Import the CSS library to style the search components.

```jsx
import React from 'react';
import { InstantSearch, SearchBox, InfiniteHits } from 'react-instantsearch';
import { instantMeiliSearch } from '@meilisearch/instant-meilisearch';
import 'instantsearch.css/themes/satellite.css';

const { searchClient } = instantMeiliSearch(
 'https://ms-adf78ae33284-106.lon.meilisearch.io',
 'a63da4928426f12639e19d62886f621130f3fa9ff3c7534c5d179f0f51c4f303'
);

const App = () => (
 <InstantSearch
 indexName="steam-videogames"
 >
 
 
 
);

const Hit = ({ hit }) => (
 <article>
 <img />
 <h1>{hit.name}</h1>
 <p>${hit.description}</p>
 </article>
);
export default App
```

Use the following CSS classes to add custom styles to your components:
`.ais-InstantSearch`, `.ais-SearchBox`, `.ais-InfiniteHits-list`, `.ais-InfiniteHits-item`

## 6. Start the app and search as you type

Start the app by running:

```bash
npm run dev
```

Now open your browser and navigate to your React app URL (e.g. `localhost:3000`), and start searching.

 <img src="/assets/images/react_quick_start/react-qs-search-ui.png" alt="React app search UI with a search bar at the top and search results for a few video games" />

Encountering issues? Check out the code in action in our [live demo](https://codesandbox.io/p/sandbox/eager-dust-f98w2w)!

## Next steps

Want to search through your own data? [Create a project](https://cloud.meilisearch.com) in the Meilisearch Dashboard. Check out our [getting started guide](/learn/getting_started/cloud_quick_start) for step-by-step instructions.

---

## Integrate a relevant search bar to your documentation

This tutorial will guide you through the steps of building a relevant and powerful search bar for your documentation 🚀

- [Run a Meilisearch instance](#run-a-meilisearch-instance)
- [Scrape your content](#scrape-your-content)
 - [Configuration file](#configuration-file)
 - [Run the scraper](#run-the-scraper)
- [Integrate the search bar](#integrate-the-search-bar)
 - [For VuePress documentation sites](#for-vuepress-documentation-sites)
 - [For all kinds of documentation](#for-all-kinds-of-documentation)
- [What's next?](#whats-next)

## Run a Meilisearch instance

First, create a new Meilisearch project on Cloud. You can also [install and run Meilisearch locally or in another cloud service](/learn/self_hosted/getting_started_with_self_hosted_meilisearch#setup-and-installation).

The host URL and the API key you will provide in the next steps correspond to the credentials of this Meilisearch instance.

## Scrape your content

The Meilisearch team provides and maintains a [scraper tool](https://github.com/meilisearch/docs-scraper) to automatically read the content of your website and store it into an index in Meilisearch.

### Configuration file

The scraper tool needs a configuration file to know what content you want to scrape. This is done by providing selectors (e.g., the `html` tag).

Here is an example of a basic configuration file:

```json
{
 "index_uid": "docs",
 "start_urls": [
 "https://www.example.com/doc/"
 ],
 "sitemap_urls": [
 "https://www.example.com/sitemap.xml"
 ],
 "stop_urls": [],
 "selectors": {
 "lvl0": {
 "selector": ".docs-lvl0",
 "global": true,
 "default_value": "Documentation"
 },
 "lvl1": {
 "selector": ".docs-lvl1",
 "global": true,
 "default_value": "Chapter"
 },
 "lvl2": ".docs-content .docs-lvl2",
 "lvl3": ".docs-content .docs-lvl3",
 "lvl4": ".docs-content .docs-lvl4",
 "lvl5": ".docs-content .docs-lvl5",
 "lvl6": ".docs-content .docs-lvl6",
 "text": ".docs-content p, .docs-content li"
 }
}
```

The `index_uid` field is the index identifier in your Meilisearch instance in which your website content is stored. The scraping tool will create a new index if it does not exist.

The `docs-content` class is the main container of the textual content in this example. Most of the time, this tag is a `<main>` or an `<article>` HTML element.

`lvlX` selectors should use the standard title tags like `h1`, `h2`, `h3`, etc. You can also use static classes. Set a unique `id` or `name` attribute to these elements.

All searchable `lvl` elements outside this main documentation container (for instance, in a sidebar) must be `global` selectors. They will be globally picked up and injected to every document built from your page.

If you use VuePress for your documentation, you can check out the [configuration file](https://github.com/meilisearch/documentation/blob/main/docs-scraper.config.json) we use in production.
In our case, the main container is `theme-default-content` and the selector titles and subtitles are `h1`, `h2`...

More [optional fields are available](https://github.com/meilisearch/docs-scraper#all-the-config-file-settings) to fit your needs.

### Run the scraper

You can run the scraper with Docker. With our local Meilisearch instance set up at [the first step](#run-a-meilisearch-instance), we run:

```bash
docker run -t --rm \
 --network=host \
 -e MEILISEARCH_HOST_URL='MEILISEARCH_URL' \
 -e MEILISEARCH_API_KEY='MASTER_KEY' \
 -v <absolute-path-to-your-config-file>:/docs-scraper/config.json \
 getmeili/docs-scraper:latest pipenv run ./docs_scraper config.json
```

If you don't want to use Docker, here are [other ways to run the scraper](https://github.com/meilisearch/docs-scraper#installation-and-usage).

`<absolute-path-to-your-config-file>` should be the **absolute** path of your configuration file defined at [the previous step](#configuration-file).

The API key should have the permissions to add documents into your Meilisearch instance. In a production environment, we recommend providing the `Default Admin API Key` as it has enough permissions to perform such requests.
_More about [Meilisearch security](/learn/security/basic_security)._

We recommend running the scraper at each new deployment of your documentation, [as we do for the Meilisearch's one](https://github.com/meilisearch/documentation/blob/main/.github/workflows/scraper.yml).

## Integrate the search bar

If your documentation is not a VuePress application, you can directly go to [this section](#for-all-kinds-of-documentation).

### For VuePress documentation sites

If you use VuePress for your documentation, we provide a [Vuepress plugin](https://github.com/meilisearch/vuepress-plugin-meilisearch). This plugin is used in production in the Meilisearch documentation.

In your VuePress project:

```bash
yarn add vuepress-plugin-Meilisearch ```

```bash
npm install vuepress-plugin-Meilisearch ```

In your `config.js` file:

```js
module.exports = {
 plugins: [
 [
 "vuepress-plugin-meilisearch",
 {
 "hostUrl": "<your-meilisearch-host-url>",
 "apiKey": "<your-meilisearch-api-key>",
 "indexUid": "docs"
 }
 ],
 ],
}
```

The `hostUrl` and the `apiKey` fields are the credentials of the Meilisearch instance. Following on from this tutorial, they are respectively `MEILISEARCH_URL` and `MASTER_KEY`.

`indexUid` is the index identifier in your Meilisearch instance in which your website content is stored. It has been defined in the [config file](#configuration-file).

These three fields are mandatory, but more [optional fields are available](https://github.com/meilisearch/vuepress-plugin-meilisearch#customization) to customize your search bar.

Since the configuration file is public, we strongly recommend providing a key that can only access [the search endpoint](/reference/api/search) , such as the `Default Search API Key`, in a production environment.
Read more about [Meilisearch security](/learn/security/basic_security).

### For all kinds of documentation

If you don't use VuePress for your documentation, we provide a [front-end SDK](https://github.com/meilisearch/docs-searchbar.js) to integrate a powerful and relevant search bar to any documentation website.

![Docxtemplater search bar updating results for "HTML"](/assets/images/tuto-searchbar-for-docs/docxtemplater-searchbar-demo.gif)
_[Docxtemplater](https://docxtemplater.com/) search bar demo_

```html
<!DOCTYPE html>
<html>
 <head>
 <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/docs-searchbar.js@{version}/dist/cdn/docs-searchbar.min.css" />
 </head>

 <body>
 <input type="search" id="search-bar-input">
 <script src="https://cdn.jsdelivr.net/npm/docs-searchbar.js@{version}/dist/cdn/docs-searchbar.min.js"></script>
 <script>
 docsSearchBar({
 hostUrl: '<your-meilisearch-host-url>',
 apiKey: '<your-meilisearch-api-key>',
 indexUid: 'docs',
 inputSelector: '#search-bar-input',
 debug: true // Set debug to true if you want to inspect the dropdown
 });
 </script>
 </body>
</html>
```

The `hostUrl` and the `apiKey` fields are the credentials of the Meilisearch instance. Following on from this tutorial, they are respectively `MEILISEARCH_URL` and `MASTER_KEY`.

`indexUid` is the index identifier in your Meilisearch instance in which your website content is stored. It has been defined in the [config file](#configuration-file).
`inputSelector` is the `id` attribute of the HTML search input tag.

We strongly recommend providing a `Default Search API Key` in a production environment, which is enough to perform search requests.

Read more about [Meilisearch security](/learn/security/basic_security).

The default behavior of this library fits perfectly for a documentation search bar, but you might need [some customizations](https://github.com/meilisearch/docs-searchbar.js#customization).

For more concrete examples, you can check out this [basic HTML file](https://github.com/meilisearch/docs-searchbar.js/blob/main/playgrounds/html/index.html) or [this more advanced Vue file](https://github.com/meilisearch/vuepress-plugin-meilisearch/blob/main/MeiliSearchBox.vue).

## What's next?

At this point, you should have a working search engine on your website, congrats! 🎉
You can check [this tutorial](/guides/running_production) if you now want to run Meilisearch in production!

---

## Vue3 quick start

## 1. Create a Vue application

Run the `npm create` tool to install base dependencies and create your app folder structure.

```bash
npm create vue@latest my-app
```

## 2. Install the library of search components

Navigate to your Vue app and install `vue-instantsearch`, `@meilisearch/instant-meilisearch`, and `instantsearch.css`.

```bash
npm install vue-instantsearch @meilisearch/instant-Meilisearch instantsearch.css
```

- [Vue InstantSearch](https://github.com/algolia/instantsearch/): front-end tools to customize your search environment
- [instant-meilisearch](https://github.com/meilisearch/meilisearch-js-plugins/tree/main/packages/instant-meilisearch): Meilisearch client to connect with Vue InstantSearch
- [instantsearch.css](https://github.com/algolia/instantsearch/tree/master/packages/instantsearch.css) (optional): CSS library to add basic styles to the search components

## 3. Add InstantSearch

Include InstantSearch into `main.js` to include the Vue InstantSearch library.

```js
import { createApp } from 'vue';
import App from './App.vue';
import InstantSearch from 'vue-instantsearch/vue3/es';

const app = createApp(App);
app.use(InstantSearch);
app.mount('#app');
```

## 4. Initialize the search client

Add the code below to the `App.vue` file.

```js
<template>
 <ais-instant-search :search-client="searchClient" index-name="steam-videogames">
 </ais-instant-search>
</template>

<script>
import { instantMeiliSearch } from "@meilisearch/instant-meilisearch";

export default {
 data() {
 return {
 searchClient: instantMeiliSearch(
 'https://ms-adf78ae33284-106.lon.meilisearch.io',
 'a63da4928426f12639e19d62886f621130f3fa9ff3c7534c5d179f0f51c4f303',
 ).searchClient,
 };
 },
};
</script>
```

These URL and API key point to a public Meilisearch instance that contains data from Steam video games.

The `ais-instant-search` widget is the mandatory wrapper that allows you to configure your search. It takes two props: the `search-client` and the [`index-name`](/learn/getting_started/indexes#index-uid).

## 5. Add a search bar and list search results

Add the `ais-search-box` and `ais-hits` widgets inside the `ais-instant-search` wrapper widget.

Import the CSS library to style the search components.

```
<template>
 <ais-instant-search :search-client="searchClient" index-name="steam-videogames">
 <ais-search-box />
 <ais-hits>
 <template v-slot:item="{ item }">
 <div>
 <img :src="item.image" align="left" :alt="item.name"/>
 <h2>{{ item.name }}</h2>
 <p> {{ item.description }}</p>
 </div>
 </template>
 </ais-hits>
 </ais-instant-search>
</template>

<script>
import { instantMeiliSearch } from "@meilisearch/instant-meilisearch";
import "instantsearch.css/themes/satellite-min.css";

export default {
data() {
 return {
 searchClient: instantMeiliSearch(
 'https://ms-adf78ae33284-106.lon.meilisearch.io',
 'a63da4928426f12639e19d62886f621130f3fa9ff3c7534c5d179f0f51c4f303',
 ).searchClient,
 };
},
};
</script>
```

Use the slot directive to customize how each search result is rendered.

Use the following CSS classes to add custom styles to your components:
`.ais-InstantSearch`, `.ais-SearchBox`, `.ais-InfiniteHits-list`, `.ais-InfiniteHits-item`

## 6.Start the app and search as you type

Start the app by running:

```bash
npm run dev
```

Now open your browser, navigate to your Vue app URL (e.g., `localhost:5173`), and start searching.

 <img src="/assets/images/react_quick_start/react-qs-search-ui.png" alt="Vue app search UI with a search bar at the top and search results for a few video games" />

Encountering issues? Check out the code in action in our [live demo](https://codesandbox.io/p/sandbox/ms-vue3-is-forked-wsrkl8)!

## Next steps

Want to search through your own data? [Create a project](https://cloud.meilisearch.com) in the Meilisearch Dashboard. Check out our [getting started guide](/learn/getting_started/cloud_quick_start) for step-by-step instructions.

---

## Using HTTP/2 and SSL with Meilisearch For those willing to use HTTP/2, please be aware that it is **only possible if your server is configured with SSL certificate**.

Therefore, you will see how to launch a Meilisearch server with SSL. This tutorial gives a short introduction to do it locally, but you can as well do the same thing on a remote server.

First of all, you need the binary of Meilisearch, or you can also use docker. In the latter case, it is necessary to pass the parameters using environment variables and the SSL certificates via a volume.

A tool to generate SSL certificates is also required. In this How To, you will use [mkcert](https://github.com/FiloSottile/mkcert). However, if on a remote server, you can also use certbot or certificates signed by a Certificate Authority.

Then, use `curl` to do requests. It is a simple way to specify that you want to send HTTP/2 requests by using the `--http2` option.

## Try to use HTTP/2 without SSL

Start by running the binary.

```bash
./Meilisearch ```

And then, send a request.

[cURL example omitted]

You will get the following answer from the server:

```bash
* Trying ::1...
* TCP_NODELAY set
* Connection failed
* connect to ::1 port 7700 failed: Connection refused
* Trying 127.0.0.1...
* TCP_NODELAY set
* Connected to localhost (127.0.0.1) port 7700 (#0)
> GET /indexes HTTP/1.1
> Host: localhost:7700
> User-Agent: curl/7.64.1
> Accept: */*
> Connection: Upgrade, HTTP2-Settings
> Upgrade: h2c
> HTTP2-Settings: AAMAAABkAARAAAAAAAIAAAAA
>
< HTTP/1.1 200 OK
< content-length: 2
< content-type: application/json
< date: Fri, 17 Jul 2020 11:01:02 GMT
<
* Connection #0 to host localhost left intact
[]* Closing connection 0
```

You can see on line `> Connection: Upgrade, HTTP2-Settings` that the server tries to upgrade to HTTP/2, but is unsuccessful.
The answer `< HTTP/1.1 200 OK` indicates that the server still uses HTTP/1.

## Try to use HTTP/2 with SSL

This time, start by generating the SSL certificates. mkcert creates two files: `127.0.0.1.pem` and `127.0.0.1-key.pem`.

```bash
mkcert '127.0.0.1'
```

Then, use the certificate and the key to configure Meilisearch with SSL.

```bash
./Meilisearch --ssl-cert-path ./127.0.0.1.pem --ssl-key-path ./127.0.0.1-key.pem
```

Next, make the same request as above but change `http://` to `https://`.

[cURL example omitted]

You will get the following answer from the server:

```bash
* Trying ::1...
* TCP_NODELAY set
* Connection failed
* connect to ::1 port 7700 failed: Connection refused
* Trying 127.0.0.1...
* TCP_NODELAY set
* Connected to localhost (127.0.0.1) port 7700 (#0)
* ALPN, offering h2
* ALPN, offering http/1.1
* successfully set certificate verify locations:
* CAfile: /etc/ssl/cert.pem
 CApath: none
* TLSv1.2 (OUT), TLS handshake, Client hello (1):
* TLSv1.2 (IN), TLS handshake, Server hello (2):
* TLSv1.2 (IN), TLS handshake, Certificate (11):
* TLSv1.2 (IN), TLS handshake, Server key exchange (12):
* TLSv1.2 (IN), TLS handshake, Server finished (14):
* TLSv1.2 (OUT), TLS handshake, Client key exchange (16):
* TLSv1.2 (OUT), TLS change cipher, Change cipher spec (1):
* TLSv1.2 (OUT), TLS handshake, Finished (20):
* TLSv1.2 (IN), TLS change cipher, Change cipher spec (1):
* TLSv1.2 (IN), TLS handshake, Finished (20):
* SSL connection using TLSv1.2 / ECDHE-RSA-AES256-GCM-SHA384
* ALPN, server accepted to use h2
* Server certificate:
* subject: O=mkcert development certificate; OU=quentindequelen@s-iMac (Quentin de Quelen)
* start date: Jun 1 00:00:00 2019 GMT
* expire date: Jul 17 10:38:53 2030 GMT
* issuer: O=mkcert development CA; OU=quentindequelen@s-iMac (Quentin de Quelen); CN=mkcert quentindequelen@s-iMac (Quentin de Quelen)
* SSL certificate verify result: unable to get local issuer certificate (20), continuing anyway.
* Using HTTP2, server supports multi-use
* Connection state changed (HTTP/2 confirmed)
* Copying HTTP/2 data in stream buffer to connection buffer after upgrade: len=0
* Using Stream ID: 1 (easy handle 0x7ff601009200)
> GET /indexes HTTP/2
> Host: localhost:7700
> User-Agent: curl/7.64.1
> Accept: */*
>
* Connection state changed (MAX_CONCURRENT_STREAMS == 4294967295)!
< HTTP/2 200
< content-length: 2
< content-type: application/json
< date: Fri, 17 Jul 2020 11:06:27 GMT
<
* Connection #0 to host localhost left intact
[]* Closing connection 0
```

You can see that the server now supports HTTP/2.

```bash
* Using HTTP2, server supports multi-use
* Connection state changed (HTTP/2 confirmed)
```

The server successfully receives HTTP/2 requests.

```bash
< HTTP/2 200
```

---

## Improve relevancy when working with large documents

Meilisearch is optimized for handling paragraph-sized chunks of text. Datasets with many documents containing large amounts of text may lead to reduced search result relevancy.

In this guide, you will see how to use JavaScript with Node.js to split a single large document and configure Meilisearch with a distinct attribute to prevent duplicated results.

## Requirements

- A running Meilisearch project
- A command-line console
- Node.js v18

## Dataset

<a id="downloadstories" href="/assets/datasets/stories.json" download="stories.json">`stories.json`</a> contains two documents, each storing the full text of a short story in its `text` field:

```json
[
 {
 "id": 0,
 "title": "A Haunted House",
 "author": "Virginia Woolf",
 "text": "Whatever hour you woke there was a door shutting. From room to room they went, hand in hand, lifting here, opening there, making sure—a ghostly couple.\n\n \"Here we left it,\" she said. And he added, \"Oh, but here too!\" \"It's upstairs,\" she murmured. \"And in the garden,\" he whispered. \"Quietly,\" they said, \"or we shall wake them.\"\n\nBut it wasn't that you woke us. Oh, no. \"They're looking for it; they're drawing the curtain,\" one might say, and so read on a page or two. \"Now they've found it,\" one would be certain, stopping the pencil on the margin. And then, tired of reading, one might rise and see for oneself, the house all empty, the doors standing open, only the wood pigeons bubbling with content and the hum of the threshing machine sounding from the farm. \"What did I come in here for? What did I want to find?\" My hands were empty. \"Perhaps it's upstairs then?\" The apples were in the loft. And so down again, the garden still as ever, only the book had slipped into the grass.\n\nBut they had found it in the drawing room. Not that one could ever see them. The window panes reflected apples, reflected roses; all the leaves were green in the glass. If they moved in the drawing room, the apple only turned its yellow side. Yet, the moment after, if the door was opened, spread about the floor, hung upon the walls, pendant from the ceiling—what? My hands were empty. The shadow of a thrush crossed the carpet; from the deepest wells of silence the wood pigeon drew its bubble of sound. \"Safe, safe, safe,\" the pulse of the house beat softly. \"The treasure buried; the room ...\" the pulse stopped short. Oh, was that the buried treasure?\n\nA moment later the light had faded. Out in the garden then? But the trees spun darkness for a wandering beam of sun. So fine, so rare, coolly sunk beneath the surface the beam I sought always burnt behind the glass. Death was the glass; death was between us; coming to the woman first, hundreds of years ago, leaving the house, sealing all the windows; the rooms were darkened. He left it, left her, went North, went East, saw the stars turned in the Southern sky; sought the house, found it dropped beneath the Downs. \"Safe, safe, safe,\" the pulse of the house beat gladly. \"The Treasure yours.\"\n\nThe wind roars up the avenue. Trees stoop and bend this way and that. Moonbeams splash and spill wildly in the rain. But the beam of the lamp falls straight from the window. The candle burns stiff and still. Wandering through the house, opening the windows, whispering not to wake us, the ghostly couple seek their joy.\n\n\"Here we slept,\" she says. And he adds, \"Kisses without number.\" \"Waking in the morning—\" \"Silver between the trees—\" \"Upstairs—\" \"In the garden—\" \"When summer came—\" \"In winter snowtime—\" The doors go shutting far in the distance, gently knocking like the pulse of a heart.\n\nNearer they come; cease at the doorway. The wind falls, the rain slides silver down the glass. Our eyes darken; we hear no steps beside us; we see no lady spread her ghostly cloak. His hands shield the lantern. \"Look,\" he breathes. \"Sound asleep. Love upon their lips.\"\n\nStooping, holding their silver lamp above us, long they look and deeply. Long they pause. The wind drives straightly; the flame stoops slightly. Wild beams of moonlight cross both floor and wall, and, meeting, stain the faces bent; the faces pondering; the faces that search the sleepers and seek their hidden joy.\n\n\"Safe, safe, safe,\" the heart of the house beats proudly. \"Long years—\" he sighs. \"Again you found me.\" \"Here,\" she murmurs, \"sleeping; in the garden reading; laughing, rolling apples in the loft. Here we left our treasure—\" Stooping, their light lifts the lids upon my eyes. \"Safe! safe! safe!\" the pulse of the house beats wildly. Waking, I cry \"Oh, is this _your_ buried treasure? The light in the heart."
 },
 {
 "id": 1,
 "title": "Monday or Tuesday",
 "author": "Virginia Woolf",
 "text": "Lazy and indifferent, shaking space easily from his wings, knowing his way, the heron passes over the church beneath the sky. White and distant, absorbed in itself, endlessly the sky covers and uncovers, moves and remains. A lake? Blot the shores of it out! A mountain? Oh, perfect—the sun gold on its slopes. Down that falls. Ferns then, or white feathers, for ever and ever——\n\nDesiring truth, awaiting it, laboriously distilling a few words, for ever desiring—(a cry starts to the left, another to the right. Wheels strike divergently. Omnibuses conglomerate in conflict)—for ever desiring—(the clock asseverates with twelve distinct strokes that it is midday; light sheds gold scales; children swarm)—for ever desiring truth. Red is the dome; coins hang on the trees; smoke trails from the chimneys; bark, shout, cry \"Iron for sale\"—and truth?\n\nRadiating to a point men's feet and women's feet, black or gold-encrusted—(This foggy weather—Sugar? No, thank you—The commonwealth of the future)—the firelight darting and making the room red, save for the black figures and their bright eyes, while outside a van discharges, Miss Thingummy drinks tea at her desk, and plate-glass preserves fur coats——\n\nFlaunted, leaf-light, drifting at corners, blown across the wheels, silver-splashed, home or not home, gathered, scattered, squandered in separate scales, swept up, down, torn, sunk, assembled—and truth?\n\nNow to recollect by the fireside on the white square of marble. From ivory depths words rising shed their blackness, blossom and penetrate. Fallen the book; in the flame, in the smoke, in the momentary sparks—or now voyaging, the marble square pendant, minarets beneath and the Indian seas, while space rushes blue and stars glint—truth? or now, content with closeness?\n\nLazy and indifferent the heron returns; the sky veils her stars; then bares them."
 }
]
```

Meilisearch works best with documents under 1kb in size. This roughly translates to a maximum of two or three paragraphs of text.

## Splitting documents

Create a `split_documents.js` file in your working directory:

```js
#!/usr/bin/env node

const datasetPath = process.argv[2];
const datasetFile = fs.readFileSync(datasetPath);
const documents = JSON.parse(datasetFile);

const splitDocuments = [];

for (let documentNumber = documents.length, i = 0; i < documentNumber; i += 1) {
 const document = documents[i];
 const story = document.text;

 const paragraphs = story.split("\n\n");
 
 for (let paragraphNumber = paragraphs.length, o = 0; o < paragraphNumber; o += 1) {
 splitDocuments.push({
 "id": document.id,
 "title": document.title,
 "author": document.author,
 "text": paragraphs[o]
 });
 }
}

fs.writeFileSync("stories-split.json", JSON.stringify(splitDocuments));
```

Next, run the script on your console, specifying the path to your JSON dataset:

```sh
node ./split_documents.js ./stories.json
```

This script accepts one argument: a path pointing to a JSON dataset. It reads the file and parses each document in it. For each paragraph in a document's `text` field, it creates a new document with a new `id` and `text` fields. Finally, it writes the new documents on `stories-split.json`.

## Generating unique IDs

Right now, Meilisearch would not accept the new dataset because many documents share the same primary key.

Update the script from the previous step to create a new field, `story_id`:

```js
#!/usr/bin/env node

const datasetPath = process.argv[2];
const datasetFile = fs.readFileSync(datasetPath);
const documents = JSON.parse(datasetFile);

const splitDocuments = [];

for (let documentNumber = documents.length, i = 0; i < documentNumber; i += 1) {
 const document = documents[i];
 const story = document.text;

 const paragraphs = story.split("\n\n");
 
 for (let paragraphNumber = paragraphs.length, o = 0; o < paragraphNumber; o += 1) {
 splitDocuments.push({
 "story_id": document.id,
 "id": `${document.id}-${o}`,
 "title": document.title,
 "author": document.author,
 "text": paragraphs[o]
 });
 }
}
```

The script now stores the original document's `id` in `story_id`. It then creates a new unique identifier for each new document and stores it in the primary key field.

## Configuring distinct attribute

This dataset is now valid, but since each document effectively points to the same story, queries are likely to result in duplicated search results.

To prevent that from happening, configure `story_id` as the index's distinct attribute:

```sh
curl \
 -X PUT 'MEILISEARCH_URL/indexes/INDEX_NAME/settings/distinct-attribute' \
 -H 'Content-Type: application/json' \
 --data-binary '"story_id"'
```

Users searching this dataset will now be able to find more relevant results across large chunks of text, without any loss of performance and no duplicates.

## Conclusion

You have seen how to split large documents to improve search relevancy. You also saw how to configure a distinct attribute to prevent Meilisearch from returning duplicate results.

Though this guide used JavaScript, you can replicate the process with any programming language you are comfortable using.

---

## Implementing semantic search with LangChain

In this guide, you’ll use OpenAI’s text embeddings to measure the similarity between document properties. Then, you’ll use the LangChain framework to seamlessly integrate Meilisearch and create an application with semantic search.

## Requirements

This guide assumes a basic understanding of Python and LangChain. Beginners to LangChain will still find the tutorial accessible.

- Python (LangChain requires >= 3.8.1 and < 4.0) and the pip CLI
- A [Meilisearch >= 1.6 project](/learn/getting_started/cloud_quick_start)
- An [OpenAI API key](https://platform.openai.com/account/api-keys)

## Creating the application

Create a folder for your application with an empty `setup.py` file.

Before writing any code, install the necessary dependencies:

```bash
pip install langchain openai Meilisearch python-dotenv
```

First create a .env to store our credentials:

```
# .env

MEILI_HTTP_ADDR="your Meilisearch host"
MEILI_API_KEY="your Meilisearch API key"
OPENAI_API_KEY="your OpenAI API key"
```

Now that you have your environment variables available, create a `setup.py` file with some boilerplate code:

```python
# setup.py

import os
from dotenv import load_dotenv # remove if not using dotenv
from langchain.vectorstores import Meilisearch from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.document_loaders import JSONLoader

load_dotenv() # remove if not using dotenv

# exit if missing env vars
if "MEILI_HTTP_ADDR" not in os.environ:
 raise Exception("Missing MEILI_HTTP_ADDR env var")
if "MEILI_API_KEY" not in os.environ:
 raise Exception("Missing MEILI_API_KEY env var")
if "OPENAI_API_KEY" not in os.environ:
 raise Exception("Missing OPENAI_API_KEY env var")

# Setup code will go here 👇
```

## Importing documents and embeddings

Now that the project is ready, import some documents in Meilisearch. First, download this small movies dataset:

 Download movies-lite.json

Then, update the setup.py file to load the JSON and store it in Meilisearch. You will also use the OpenAI text search models to generate vector embeddings.

To use vector search, we need to set the embedders index setting. In this case, you are using an `userProvided` source which requires to specify the size of the vectors in a `dimensions` field. The default model used by `OpenAIEmbeddings()` is `text-embedding-ada-002`, which has 1,536 dimensions.

```python
# setup.py

# previous code

# Load documents
loader = JSONLoader(
 file_path="./movies-lite.json",
 jq_schema=".[] | {id: .id, overview: .overview, title: .title}",
 text_content=False,
)
documents = loader.load()
print("Loaded {} documents".format(len(documents)))

# Store documents in Meilisearch embeddings = OpenAIEmbeddings()
embedders = { 
 "custom": {
 "source": "userProvided",
 "dimensions": 1536
 }
 }
embedder_name = "custom" 
vector_store = Meilisearch.from_documents(documents=documents, embedding=embeddings, embedders=embedders, embedder_name=embedder_name)

print("Started importing documents")
```

Your Meilisearch instance will now contain your documents. Meilisearch runs tasks like document import asynchronously, so you might need to wait a bit for documents to be available. Consult [the asynchronous operations explanation](/learn/async/asynchronous_operations) for more information on how tasks work.

## Performing similarity search

Your database is now populated with the data from the movies dataset. Create a new `search.py` file to make a semantic search query: searching for documents using similarity search.

```python
# search.py

import os
from dotenv import load_dotenv
from langchain.vectorstores import Meilisearch from langchain.embeddings.openai import OpenAIEmbeddings
import Meilisearch load_dotenv()

# You can use the same code as `setup.py` to check for missing env vars

# Create the vector store
client = meilisearch.Client(
 url=os.environ.get("MEILI_HTTP_ADDR"),
 api_key=os.environ.get("MEILI_API_KEY"),
)
embeddings = OpenAIEmbeddings()
vector_store = Meilisearch(client=client, embedding=embeddings)

# Make similarity search
embedder_name = "custom"
query = "superhero fighting evil in a city at night"
results = vector_store.similarity_search(
 query=query,
 embedder_name=embedder_name,
 k=3,
)

# Display results
for result in results:
 print(result.page_content)
```

Run `search.py`. If everything is working correctly, you should see an output like this:

```
{"id": 155, "title": "The Dark Knight", "overview": "Batman raises the stakes in his war on crime. With the help of Lt. Jim Gordon and District Attorney Harvey Dent, Batman sets out to dismantle the remaining criminal organizations that plague the streets. The partnership proves to be effective, but they soon find themselves prey to a reign of chaos unleashed by a rising criminal mastermind known to the terrified citizens of Gotham as the Joker."}
{"id": 314, "title": "Catwoman", "overview": "Liquidated after discovering a corporate conspiracy, mild-mannered graphic artist Patience Phillips washes up on an island, where she's resurrected and endowed with the prowess of a cat -- and she's eager to use her new skills ... as a vigilante. Before you can say \"cat and mouse,\" handsome gumshoe Tom Lone is on her tail."}
{"id": 268, "title": "Batman", "overview": "Batman must face his most ruthless nemesis when a deformed madman calling himself \"The Joker\" seizes control of Gotham's criminal underworld."}
```

Congrats 🎉 You managed to make a similarity search using Meilisearch as a LangChain vector store.

## Going further

Using Meilisearch as a LangChain vector store allows you to load documents and search for them in different ways:

- [Import documents from text](https://python.langchain.com/docs/integrations/vectorstores/meilisearch#adding-text-and-embeddings)
- [Similarity search with score](https://python.langchain.com/docs/integrations/vectorstores/meilisearch#similarity-search-with-score)
- [Similarity search by vector](https://python.langchain.com/docs/integrations/vectorstores/meilisearch#similarity-search-by-vector)

For additional information, consult:

[Meilisearch Python SDK docs](https://python-sdk.meilisearch.com/)

Finally, should you want to use Meilisearch's vector search capabilities without LangChain or its hybrid search feature, refer to the [dedicated tutorial](/learn/ai_powered_search/getting_started_with_ai_search).

---

## Laravel multitenancy guide

This guide will walk you through implementing search in a multitenant Laravel application. We'll use the example of a customer relationship manager (CRM) application that allows users to store contacts.

## Requirements

This guide requires:

- A Laravel 10 application with [Laravel Scout](https://laravel.com/docs/10.x/scout) configured to use the `meilisearch` driver
- A Meilisearch server running — see our [quick start](/learn/getting_started/cloud_quick_start)
- A search API key — available in your Meilisearch dashboard
- A search API key UID — retrieve it using the [keys endpoints](/reference/api/keys)

Prefer self-hosting? Read our [installation guide](/learn/self_hosted/install_meilisearch_locally).

## Models & relationships

Our example CRM is a multitenant application, where each user can only access data belonging to their organization.

On a technical level, this means:

- A `User` model that belongs to an `Organization`
- A `Contact` model that belongs to an `Organization` (can only be accessed by users from the same organization)
- An `Organization` model that has many `User`s and many `Contact`s

With that in mind, the first step is to define such these models and their relationship:

In `app/Models/Contact.php`:

```php
<?php

namespace App\Models;

use Laravel\Scout\Searchable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Contact extends Model
{
 use Searchable;

 public function organization(): BelongsTo
 {
 return $this->belongsTo(Organization::class, 'organization_id');
 }
}
```

In `app/Models/User.php`:

```php
<?php

namespace App\Models;

use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

class User extends Authenticatable
{
 use HasApiTokens, Notifiable;

 /**
 * The attributes that are mass assignable.

 * @var array<int, string>
 */
 protected $fillable = [
 'name',
 'email',
 'password',
 ];

 /**
 * The attributes that should be hidden for serialization.

 * @var array<int, string>
 */
 protected $hidden = [
 'password',
 'remember_token',
 ];

 /**
 * The attributes that should be cast.

 * @var array<string, string>
 */
 protected $casts = [
 'email_verified_at' => 'datetime',
 'password' => 'hashed',
 ];

 public function organization()
 {
 return $this->belongsTo(Organization::class, 'organization_id');
 }
}
```

And in `app/Models/Organization.php`:

```php
<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Organization extends Model
{
 public function contacts(): HasMany
 {
 return $this->hasMany(Contact::class);
 }
}
```

Now you have a solid understanding of your application's models and their relationships, you are ready to generate tenant tokens.

## Generating tenant tokens

Currently, all `User`s can search through data belonging to all `Organizations`. To prevent that from happening, you need to generate a tenant token for each organization. You can then use this token to authenticate requests to Meilisearch and ensure that users can only access data from their organization. All `User` within the same `Organization` will share the same token.

In this guide, you will generate the token when the organization is retrieved from the database. If the organization has no token, you will generate one and store it in the `meilisearch_token` attribute.

Update `app/Models/Organization.php`:

```php
<?php

namespace App\Models;

use DateTime;
use Laravel\Scout\EngineManager;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Facades\Log;

class Organization extends Model
{

 public function contacts(): HasMany
 {
 return $this->hasMany(Contact::class);
 }

 protected static function booted()
 {
 static::retrieved(function (Organization $organization) {
 // You may want to add some logic to skip generating tokens in certain environments
 if (env('SCOUT_DRIVER') === 'array' && env('APP_ENV') === 'testing') {
 $organization->meilisearch_token = 'fake-tenant-token';
 return;
 }

 // Early return if the organization already has a token
 if ($organization->meilisearch_token) {
 Log::debug('Organization ' . $organization->id . ': already has a token');
 return;
 }
 Log::debug('Generating tenant token for organization ID: ' . $organization->id);

 // The object belows is used to generate a tenant token that:
 // • applies to all indexes
 // • filters only documents where `organization_id` is equal to this org ID
 $searchRules = (object) [
 '*' => (object) [
 'filter' => 'organization_id = ' . $organization->id,
 ]
 ];

 // Replace with your own Search API key and API key UID
 $meiliApiKey = env('MEILISEARCH_SEARCH_KEY');
 $meiliApiKeyUid = env('MEILISEARCH_SEARCH_KEY_UID');

 // Generate the token
 $token = self::generateMeiliTenantToken($meiliApiKeyUid, $searchRules, $meiliApiKey);

 // Save the token in the database
 $organization->meilisearch_token = $token;
 $organization->save();
 });
 }

 protected static function generateMeiliTenantToken($meiliApiKeyUid, $searchRules, $meiliApiKey)
 {
 $Meilisearch = resolve(EngineManager::class)->engine();

 return $meilisearch->generateTenantToken(
 $meiliApiKeyUid,
 $searchRules,
 [
 'apiKey' => $meiliApiKey,
 'expiresAt' => new DateTime('2030-12-31'),
 ]
 );
 }
}
```

Now the `Organization` model is generating tenant tokens, you need to provide the front-end with these tokens so that it can access Meilisearch securely.

## Using tenant tokens with Laravel Blade

Use [view composers](https://laravel.com/docs/10.x/views#view-composers) to provide views with your search token. This way, you ensure the token is available in all views, without having to pass it manually.

If you prefer, you can pass the token manually to each view using the `with` method.

Create a new `app/View/Composers/AuthComposer.php` file:

```php
<?php

namespace App\View\Composers;

use App\Models\User;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Vite;
use Illuminate\View\View;

class AuthComposer
{
 /**
 * Create a new profile composer.
 */
 public function __construct() {}

 /**
 * Bind data to the view.
 */
 public function compose(View $view): void
 {
 $user = Auth::user();
 $view->with([
 'meilisearchToken' => $user->organization->meilisearch_token,
 ]);
 }
}
```

Now, register this view composer in the `AppServiceProvider`:

```php
<?php

namespace App\Providers;

use App\View\Composers\AuthComposer;
use Illuminate\Support\Facades\View;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
 /**
 * Register any application services.
 */
 public function register(): void
 {
 //
 }

 /**
 * Bootstrap any application services.
 */
 public function boot(): void
 {
 // Use this view composer in all views
 View::composer('*', AuthComposer::class);
 }
}
```

And ta-da! All views now have access to the `meilisearchToken` variable. You use this variable in your front end.

## Building the search UI

This guide uses **Vue InstantSearch** to build your search interface. Vue InstantSearch is a set of components and helpers to build a search UI in Vue applications. If you prefer other flavours of JavaScript, check out our other [front-end integrations](/guides/front_end/front_end_integration).

First, install the dependencies:

```bash
npm install vue-instantsearch @meilisearch/instant-Meilisearch ```

Now, create a Vue app that uses Vue InstantSearch. Open a new `resources/js/vue-app.js` file:

```js
import { createApp } from 'vue'
import InstantSearch from 'vue-instantsearch/vue3/es'
import Meilisearch from './components/Meilisearch.vue'

const app = createApp({
 components: {
 Meilisearch }
})

app.use(InstantSearch)
app.mount('#vue-app')
```

This file initializes your Vue app and configures it to use Vue InstantSearch. It also registers the `Meilisearch` component you will create next.

The `Meilisearch` component is responsible for initializing a Vue Instantsearch client. It uses the `@meilisearch/instant-meilisearch` package to create a search client compatible with Instantsearch.

Create it in `resources/js/components/Meilisearch.vue`:

```vue
<script setup lang="ts">
import { instantMeiliSearch } from "@meilisearch/instant-meilisearch"

const props = defineProps<{
 host: string,
 apiKey: string,
 indexName: string,
}>()

const { searchClient } = instantMeiliSearch(props.host, props.apiKey)
</script>

<template>
 <ais-instant-search :search-client="searchClient" :index-name="props.indexName">
 
 <slot name="default"></slot>
 </ais-instant-search>
</template>
```

You can use the `Meilisearch` component it in any Blade view by providing it with the tenant token. Don't forget to add the `@vite` directive to include the Vue app in your view.

```blade

<div id="vue-app">
 <Meilisearch index-name="contacts" api-key="{{ $meilisearchToken }}" host="https://edge.meilisearch.com">
 </meilisearch>
</div>

@push('scripts')
 @vite('resources/js/vue-app.js')
@endpush
```

Et voilà! You now have a search interface i.e. secure and multitenant. Users can only access data from their organization, and you can rest assured that data from other tenants is safe.

## Conclusion

In this guide, you saw how to implement secure, multitenant search in a Laravel application. You then generated tenant tokens for each organization and used them to secure access to Meilisearch. You also built a search interface using Vue InstantSearch and provided it with the tenant token.

All the code in this guide is a simplified example of what we implemented in the [Laravel CRM](https://saas.meilisearch.com/?utm_campaign=oss&utm_source=docs&utm_medium=laravel-multitenancy) example application. Find the full code on [GitHub](https://github.com/meilisearch/saas-demo).

---

## Laravel Scout guide

In this guide, you will see how to setup [Laravel Scout](https://laravel.com/docs/10.x/scout) to use Meilisearch in your Laravel 10 application.

## Prerequisites

Before you start, make sure you have the following installed on your machine:

- PHP
- [Composer](https://getcomposer.org/)

You will also need a Laravel application. If you don't have one, you can create a new one by running the following command:

```sh
composer create-project laravel/laravel my-application
```

## Installing Laravel Scout

Laravel comes with out-of-the-box full-text search capabilities via Laravel Scout.

To enable it, navigate to your Laravel application directory and install Scout via the Composer package manager:

```sh
composer require laravel/scout
```

After installing Scout, you need to publish the Scout configuration file. You can do this by running the following `artisan` command:

```sh
php artisan vendor:publish --provider="Laravel\Scout\ScoutServiceProvider"
```

This command should create a new configuration file in your application directory: `config/scout.php`.

## Configuring the Laravel Scout driver

Now you need to configure Laravel Scout to use the Meilisearch driver. First, install the dependencies required to use Scout with Meilisearch via Composer:

```sh
composer require meilisearch/meilisearch-php http-interop/http-factory-guzzle
```

Then, update the environment variables in your `.env` file:

```sh
SCOUT_DRIVER=Meilisearch # Use the host below if you're running Meilisearch via Laravel Sail
MEILISEARCH_HOST=http://meilisearch:7700
MEILISEARCH_KEY=masterKey
```

### Local development

Laravel’s official Docker development environment, Laravel Sail, comes with a Meilisearch service out-of-the-box. note: when running Meilisearch via Sail, Meilisearch’s host is `http://meilisearch:7700` (instead of say, `http://localhost:7700`).

Check out Docker [Bridge network driver](https://docs.docker.com/network/drivers/bridge/#differences-between-user-defined-bridges-and-the-default-bridge) documentation for further detail.

### Running in production

For production use cases, we recommend using a managed Meilisearch via [Cloud](https://www.meilisearch.com/cloud?utm_campaign=laravel&utm_source=docs&utm_medium=laravel-scout-guide). On Cloud, you can find your host URL in your project settings.

Read the [Cloud quick start](/learn/getting_started/cloud_quick_start).

If you prefer to self-host, read our guide for [running Meilisearch in production](/guides/running_production).

## Making Eloquent models searchable

With Scout installed and configured, add the `Laravel\Scout\Searchable` trait to your Eloquent models to make them searchable. This trait will use Laravel’s model observers to keep the data in your model in sync with Meilisearch.

Here’s an example model:

```php
<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Laravel\Scout\Searchable;

class Contact extends Model
{
 use Searchable;
}
```

To configure which fields to store in Meilisearch, use the `toSearchableArray` method. You can use this technique to store a model and its relationships’ data in the same document.

The example below shows how to store a model's relationships data in Meilisearch:

```php
<?php

namespace App\Models;

use App\Models\Company;
use Laravel\Scout\Searchable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Contact extends Model
{
 use Searchable;

 public function company(): BelongsTo
 {
 return $this->belongsTo(Company::class);
 }

 public function toSearchableArray(): array
 {
 // All model attributes are made searchable
 $array = $this->toArray();

 // Then we add some additional fields
 $array['organization_id'] = $this->company->organization->id;
 $array['company_name'] = $this->company->name;
 $array['company_url'] = $this->company->url;

 return $array;
 }
}
```

## Configuring filterable and sortable attributes

Configure which attributes are [filterable](/learn/filtering_and_sorting/filter_search_results) and [sortable](/learn/filtering_and_sorting/sort_search_results) via your Meilisearch index settings.

In Laravel, you can configure your index settings via the `config/scout.php` file:

```php
<?php

use App\Models\Contact;

return [
 // Other Scout configuration...

 'meilisearch' => [
 'host' => env('MEILISEARCH_HOST', 'https://edge.meilisearch.com'),
 'key' => env('MEILISEARCH_KEY'),
 'index-settings' => [
 Contact::class => [
 'filterableAttributes' => ['organization_id'],
 'sortableAttributes' => ['name', 'company_name']
 ],
 ],
 ],
];
```

The example above updates Meilisearch index settings for the `Contact` model:

- it makes the `organization_id` field filterable
- it makes the `name` and `company_name` fields sortable

After changing your index settings, you will need to synchronize your Scout index settings.

## Synchronizing your index settings

To synchronize your index settings, run the following command:

```sh
php artisan scout:sync-index-settings
```

## Example usage

You built an example application to demonstrate how to use Meilisearch with Laravel Scout. It showcases an app-wide search in a CRM (Customer Relationship Management) application.

 <a href="https://saas.meilisearch.com/?utm_campaign=laravel&utm_source=docs&utm_medium=laravel-scout-guide">
 <img src="/assets/images/demos/saas-demo-screenshot.png" alt="Laravel Scout example application" />
 </a>

This demo application uses the following features:

- [Multi-search](/reference/api/multi_search) (search across multiple indexes)
- [Multi-tenancy](/learn/security/multitenancy_tenant_tokens)
- [Filtering](/learn/filtering_and_sorting/filter_search_results)
- [Sorting](/learn/filtering_and_sorting/sort_search_results)

Of course, the code is open-sourced on [Github](https://github.com/meilisearch/saas-demo). 🎉

---

## Node.js multitenancy guide

This guide will walk you through implementing search in a multitenant Node.js application handling sensitive medical data.

## What is multitenancy?

In Meilisearch, you might have one index containing data belonging to many distinct tenants. In such cases, your tenants must only be able to search through their own documents. You can implement this using [tenant tokens](/learn/security/multitenancy_tenant_tokens).

## Requirements

- [Node.js](https://nodejs.org/en) and a package manager like `npm`, `yarn`, or `pnpm`
- [Meilisearch JavaScript SDK](/learn/resources/sdks)
- A Meilisearch server running — see our [quick start](/learn/getting_started/cloud_quick_start)
- A search API key — available in your Meilisearch dashboard
- A search API key UID — retrieve it using the [keys endpoints](/reference/api/keys)

Prefer self-hosting? Read our [installation guide](/learn/self_hosted/install_meilisearch_locally).

## Data models

This guide uses a simple data model to represent medical appointments. The documents in the Meilisearch index will look like this:

```json
[
 {
 "id": 1,
 "patient": "John",
 "details": "I think I caught a cold. Can you help me?",
 "status": "pending"
 },
 {
 "id": 2,
 "patient": "Zia",
 "details": "I'm suffering from fever. I need an appointment ASAP.",
 "status": "pending"
 },
 {
 "id": 3,
 "patient": "Kevin",
 "details": "Some confidential information Kevin has shared.",
 "status": "confirmed"
 }
]
```

For the purpose of this guide, we assume documents are stored in an `appointments` index.

## Creating a tenant token

The first step is generating a tenant token that will allow a given patient to search only for their appointments. To achieve this, you must first create a tenant token that filters results based on the patient's ID.

Create a `search.js` file and use the following code to generate a tenant token:

```js
// search.js

import { Meilisearch } from 'meilisearch'

const apiKey = 'YOUR_SEARCH_API_KEY'
const apiKeyUid = 'YOUR_SEARCH_API_KEY_UID'
const indexName = 'appointments'

const client = new Meilisearch({
 host: 'https://edge.meilisearch.com', // Your Meilisearch host
 apiKey: apiKey
})

export function createTenantToken(patientName) {
 const searchRules = {
 [indexName]: {
 'filter': `patient = ${patientName}`
 }
 }

 const tenantToken = client.generateTenantToken(
 apiKeyUid,
 searchRules,
 {
 expiresAt: new Date('2030-01-01'), // Choose an expiration date
 apiKey: apiKey,
 }
 )
 return tenantToken
}
```

When Meilisearch gets a search query with a tenant token, it decodes it and applies the search rules to the search request. In this example, the results are filtered by the `patient` field. This means that a patient can only search for their own appointments.

## Using the tenant token

Now that you have a tenant token, use it to perform searches. To achieve this, you will need to:

- On the server: create an endpoint to send the token to your front-end
- On the client: retrieve the token and use it to perform searches

### Serving the tenant token

This guide uses [Express.js](https://expressjs.com/en/starter/installing.html) to create the server. You can install `express` by running:

```sh
# with NPM
npm i express
# with Yarn
yarn add express
# with pnpm
pnpm add express
```

Then, add the following code in a `server.js` file:

```js
// server.js

import express from 'express'
import { createTenantToken } from './search.js'

const server = express()

server.get('/token', async (request, response) => {
 const { id: patientId } = request.query
 const token = createTenantToken(patientId)
 return response.json({ token });
})

server.listen(3000, () => {
 console.log('Server is running on port 3000')
})
```

This code creates an endpoint at `http://localhost:3000/token` that accepts an `id` query parameter and returns a tenant token.

### Making a search

Now that we have an endpoint, you will use it to retrieve the tenant token in your front-end application. This guide uses [InstantSearch.js](/guides/front_end/front_end_integration) to create a search interface. You will use CDN links to include InstantSearch.js and the Meilisearch InstantSearch.js connector in your HTML file.

Create `client.html` file and insert this code:

```html
<!DOCTYPE html>
<html lang="en">
 <head>
 <meta charset="utf-8" />
 <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@meilisearch/instant-meilisearch/templates/basic_search.css" />
 </head>
 <body>
 <div class="wrapper">
 <div id="searchbox" focus></div>
 <div id="hits"></div>
 </div>
 </body>
 <script src="https://cdn.jsdelivr.net/npm/@meilisearch/instant-meilisearch/dist/instant-meilisearch.umd.min.js"></script>
 <script src="https://cdn.jsdelivr.net/npm/instantsearch.js@4"></script>
 <script>
 document.addEventListener('DOMContentLoaded', async () => {
 const patientId = 1 // Replace with the patient's ID
 const response = await fetch(`http://localhost:3000/token?id=${patientId}`)
 const { token } = await response.json()

 const search = instantsearch({
 indexName: 'appointments',
 searchClient: instantMeiliSearch(
 'https://edge.meilisearch.com',
 token
 ).searchClient
 })

 search.addWidgets([
 instantsearch.widgets.searchBox({
 container: "#searchbox"
 }),
 instantsearch.widgets.hits({
 container: "#hits",
 templates: {
 item: `
 <div>
 <div class="hit-name">
 {{#helpers.highlight}}{ "attribute": "patient" }{{/helpers.highlight}}
 </div>
 <div class="hit-description">
 {{#helpers.highlight}}{ "attribute": "details" }{{/helpers.highlight}}
 </div>
 </div>
 `
 }
 })
 ])

 search.start()
 })
 </script>
</html>
```

Ta-da! You have successfully implemented a secure, multitenant search in your Node.js application. Users will only be able to search for documents that belong to them.

## Conclusion

In this guide, you saw how to implement secure, multitenant search in a Node.js application. You then created an endpoint to generate tenant tokens for each user. You also built a search interface with InstantSearch to make searches using the tenant token.

All the code in this guide is a taken from our [multitenacy example](https://tenant-token.meilisearch.com/?utm_campaign=oss&utm_source=docs&utm_medium=node-multitenancy) application. The code is available on [GitHub](https://github.com/meilisearch/tutorials/tree/main/src/tenant-token-tutorial).

---

## Postman collection for Meilisearch Are you tired of using the `curl` command in your terminal to test Meilisearch? It can be tedious to re-write every route when wanting to try out an API.

Postman is a platform that lets you create HTTP requests you can easily reuse and share with everyone. We provide a <a href="/docs/assets/misc/meilisearch-collection-postman.json" download="meilisearch-collection-postman.json">Postman collection</a> containing all the routes of the Meilisearch API! 🚀

If you don't have Postman already, you can [download it here](https://www.postman.com/downloads/). It's free and available on many OS distributions.

## Import the collection

Once you have downloaded the <a href="/docs/assets/misc/meilisearch-collection-postman.json" download="meilisearch-collection-postman.json">Postman collection</a>, you need to import it into Postman.

 <img src="/assets/images/postman/import.png" alt="The 'Import' button" />

## Edit the configuration

 <img src="/assets/images/postman/edit.png" alt="Selecting 'Edit' from the overflow menu" />

Set the "Token" if needed (set to `masterKey` by default):

 <img src="/assets/images/postman/set_token.png" alt="The 'Token' field set to masterKey and 'Type' to Bearer Token in the 'Authorization' tab." />

Set `url` (set to Meilisearch's local port by default) and `indexUID` (set to `indexUID` by default):

 <img src="/assets/images/postman/set_variables.png" alt="Setting the 'URL' to http://localhost:7700/ and 'indexUID' to indexUId in the Variables tab." />

The `url` and `indexUID` variables are used in all the collection routes, like in this one:

 <img src="/assets/images/postman/url.png" alt="Highlighting {{url}} and {{indexUID}}" />

## Start to use it

You can now [run your Meilisearch instance](/learn/self_hosted/getting_started_with_self_hosted_meilisearch#setup-and-installation) and create your first index:

 <img src="/assets/images/postman/create_index.png" alt="The 'Send' button" />

---

## Ruby on Rails quick start

Integrate Meilisearch into your Ruby on Rails app.

## 1. Create a Meilisearch project

[Create a project](https://cloud.meilisearch.com) in the Cloud dashboard. Check out our [getting started guide](/learn/getting_started/cloud_quick_start) for step-by-step instructions.

If you prefer to use the self-hosted version of Meilisearch, you can follow the [quick start](https://www.meilisearch.com/docs/learn/self_hosted/getting_started_with_self_hosted_meilisearch) tutorial.

## 2. Create a Rails app

Ensure your environment uses at least Ruby 2.7.0 and Rails 6.1.

```bash
rails new blog
```

## 3. Install the meilisearch-rails gem

Navigate to your Rails app and install the `meilisearch-rails` gem.

```bash
bundle add meilisearch-rails
```

## 4. Add your Meilisearch credentials

Run the following command to create a `config/initializers/meilisearch.rb` file.

```bash
bin/rails meilisearch:install
```

Then add your Meilisearch URL and [Default Admin API Key](/learn/security/basic_security#obtaining-api-keys). On Cloud, you can find your credentials in your project settings.

```Ruby
MeiliSearch::Rails.configuration = {
 meilisearch_url: '<your Meilisearch URL>',
 meilisearch_api_key: '<your Meilisearch API key>'
}
```

## 5. Generate the model and run the database migration

Create an example `Article` model and generate the migration files.

```bash
bin/rails generate model Article title:string body:text

bin/rails db:migrate
```

## 6. Index your model into Meilisearch Include the `MeiliSearch::Rails` module and the `meilisearch` block.

```Ruby
class Article < ApplicationRecord
 include MeiliSearch::Rails
 
 Meilisearch do
 # index settings
 # all attributes will be sent to Meilisearch if block is left empty
 end
end
```

This code creates an `Article` index and adds search capabilities to your `Article` model.

Once configured, `meilisearch-rails` automatically syncs your table data with your Meilisearch instance.

## 7. Create new records in the database

Use the Rails console to create new entries in the database.

```bash
bin/rails console
```

```Ruby
# Use a loop to create and save 5 unique articles with predefined titles and bodies
titles = ["Welcome to Rails", "Exploring Rails", "Advanced Rails", "Rails Tips", "Rails in Production"]
bodies = [
 "This is your first step into Ruby on Rails.",
 "Dive deeper into the Rails framework.",
 "Explore advanced features of Rails.",
 "Quick tips for Rails developers.",
 "Managing Rails applications in production environments."
]

titles.each_with_index do |title, index| article = Article.new(title: title, body: bodies[index])
 article.save # Saves the entry to the database
end
```

## 8. Start searching

### Backend search

The backend search returns ORM-compliant objects reloaded from your database.

```Ruby
# Meilisearch is typo-tolerant:
hits = Article.search('deepre')
hits.first
```

We strongly recommend using the frontend search to enjoy the swift and responsive search-as-you-type experience.

### Frontend search

For testing purposes, you can explore the records using our built-in [search preview](/learn/getting_started/search_preview).

![Searching through Rails table data with Meilisearch search preview UI](/assets/images/rails_quick_start/rails-qs-search-preview.gif)

We also provide resources to help you quickly build your own [frontend interface](/guides/front_end/front_end_integration).

## Next steps

When you're ready to use your own data, make sure to configure your [index settings](/reference/api/settings) first to follow [best practices](/learn/indexing/indexing_best_practices). For a full configuration example, see the [meilisearch-rails gem README](https://github.com/meilisearch/meilisearch-rails?tab=readme-ov-file#%EF%B8%8F-settings).

---

## Running Meilisearch in production

This tutorial will guide you through setting up a production-ready Meilisearch instance. These instructions use a DigitalOcean droplet running Debian, but should be compatible with any hosting service running a Linux distro.

[Cloud](https://www.meilisearch.com/cloud?utm_campaign=oss&utm_source=docs&utm_medium=running-production-oss) is the recommended way to run Meilisearch in production environments.

## Requirements

- A DigitalOcean droplet running Debian 12
- An SSH key pair to connect to that machine

DigitalOcean has extensive documentation on [how to use SSH to connect to a droplet](https://www.digitalocean.com/docs/droplets/how-to/connect-with-ssh/).

## Step 1: Install Meilisearch Log into your server via SSH, update the list of available packages, and install `curl`:

```sh
apt update
apt install curl -y
```

Using the latest version of a package is good security practice, especially in production environments.

Next, use `curl` to download and run the Meilisearch command-line installer:

```sh
# Install Meilisearch latest version from the script
curl -L https://install.meilisearch.com | sh
```

The Meilisearch installer is a set of scripts that ensure you will get the correct binary for your system.

Next, you need to make the binary accessible from anywhere in your system. Move the binary file into `/usr/local/bin`:

```sh
mv ./Meilisearch /usr/local/bin/
```

Meilisearch is now installed in your system, but it is not publicly accessible.

## Step 2: Create system user

Running applications as root exposes you to unnecessary security risks. To prevent that, create a dedicated user for Meilisearch:

```sh
useradd -d /var/lib/Meilisearch -s /bin/false -m -r Meilisearch ```

Then give the new user ownership of the Meilisearch binary:

```sh
chown meilisearch:Meilisearch /usr/local/bin/Meilisearch ```

## Step 3: Create a configuration file

After installing Meilisearch and taking the first step towards keeping your data safe, you need to set up a basic configuration file.

First, create the directories where Meilisearch will store its data:

```bash
mkdir /var/lib/meilisearch/data /var/lib/meilisearch/dumps /var/lib/meilisearch/snapshots
chown -R meilisearch:Meilisearch /var/lib/Meilisearch chmod 750 /var/lib/Meilisearch ```

In this tutorial, you're creating the directories in your droplet's local disk. If you are using additional block storage, create these directories there.

Next, download the default configuration to `/etc`:

[cURL example omitted]

Finally, update the following lines in the `meilisearch.toml` file so Meilisearch uses the directories you created earlier to store its data, replacing `MASTER_KEY` with a 16-byte string:

```ini
env = "production"
master_key = "MASTER_KEY"
db_path = "/var/lib/meilisearch/data"
dump_dir = "/var/lib/meilisearch/dumps"
snapshot_dir = "/var/lib/meilisearch/snapshots"
```

Remember to choose a [safe master key](/learn/security/basic_security#creating-the-master-key-in-a-self-hosted-instance) and avoid exposing it in publicly accessible locations.

You have now configured your Meilisearch instance.

## Step 4: Run Meilisearch as a service

In Linux environments, a service is a process that can be launched when the operating system is booting and which will keep running in the background. If your program stops running for any reason, Linux will immediately restart the service, helping reduce downtime.

### 4.1. Create a service file

Service files are text files that tell your operating system how to run your program.

Run this command to create a service file in `/etc/systemd/system`:

```bash
cat << EOF > /etc/systemd/system/meilisearch.service
[Unit]
Description=Meilisearch After=systemd-user-sessions.service

[Service]
Type=simple
WorkingDirectory=/var/lib/Meilisearch ExecStart=/usr/local/bin/Meilisearch --config-file-path /etc/meilisearch.toml
User=Meilisearch Group=Meilisearch Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
```

### 4.2. Enable and start service

With your service file now ready to go, activate the service using `systemctl`:

```bash
systemctl enable Meilisearch systemctl start Meilisearch ```

With `systemctl enable`, you're telling the operating system you want it to run at every boot. `systemctl start` then immediately starts the Meilisearch service.

Ensure everything is working by checking the service status:

```sh
systemctl status Meilisearch ```

You should see a message confirming your service is running:

```sh
● meilisearch.service - Meilisearch Loaded: loaded (/etc/systemd/system/meilisearch.service; enabled; vendor preset: enabled)
 Active: active (running) since Fri 2023-04-10 14:27:49 UTC; 1min 8s ago
 Main PID: 14960 (meilisearch)
```

## Step 5: Secure and finish your setup

At this point, Meilisearch is installed and running. It is also protected from eventual crashes and system restarts.

The next step is to make your instance publicly accessible.

If all the requests you send to Meilisearch are done by another application living in the same machine, you can safely skip this section.

### 5.1. Creating a reverse proxy with Nginx

A [reverse proxy](https://www.keycdn.com/support/nginx-reverse-proxy) is an application that will handle every communication between the outside world and your application. In this tutorial, you will use [Nginx](https://www.nginx.com/) as your reverse proxy to receive external HTTP requests and redirect them to Meilisearch.

First, install Nginx on your machine:

```bash
apt-get install nginx -y
```

Next, delete the default configuration file:

```bash
rm -f /etc/nginx/sites-enabled/default
```

Nginx comes with a set of default settings, such as its default HTTP port, that might conflict with Meilisearch.

Create a new configuration file specifying the reverse proxy settings:

```sh
cat << EOF > /etc/nginx/sites-enabled/Meilisearch server {
 listen 80 default_server;
 listen [::]:80 default_server;
 server_name _;
 location / {
 proxy_pass http://localhost:7700;
 }
}
EOF
```

Finally, enable the Nginx service:

```bash
systemctl daemon-reload
systemctl enable nginx
systemctl restart nginx
```

Your Meilisearch instance is now publicly available.

### 5.2. Enable HTTPS

The only remaining problem is that Meilisearch processes requests via HTTP without any additional security. This is a major security flaw that could result in an attacker accessing your data.

This tutorial assumes you have a registered domain name, and you have correctly configured its DNS's `A record` to point to your DigitalOcean droplet's IP address. Consult the [DigitalOcean DNS documentation](https://docs.digitalocean.com/products/networking/dns/getting-started/dns-registrars/) for more information.

Use [certbot](https://certbot.eff.org/) to configure enable HTTPS in your server.

First, install the required packages on your system:

```bash
sudo apt install certbot python3-certbot-nginx -y
```

Next, run certbot:

```bash
certbot --nginx
```

Enter your email address, agree to the Terms and Conditions, and choose your domain. When prompted if you want to automatically redirect HTTP traffic, choose option `2: Redirect`.

Certbot will finish configuring Nginx. Once it is done, all traffic to your server will use HTTPS and you will have finished securing your Meilisearch instance.

Your security certificate must be renewed every 90 days. Certbot schedules the renewal automatically. Run a test to verify this process is in place:

```bash
sudo certbot renew --dry-run
```

If this command returns no errors, you have successfully enabled HTTPS in your Nginx server.

## Conclusion

You have followed the main steps to provide a safe and stable service. Your Meilisearch instance is now up and running in a safe and publicly accessible environment thanks to the combination of a reverse proxy, HTTPS, and Meilisearch's built-in security keys.

---

## Strapi v4 guide

This tutorial will show you how to integrate Meilisearch with [Strapi](https://strapi.io/) to create a search-based web app. First, you will use Strapi’s quick start guide to create a restaurant collection, and then search this collection with Meilisearch.

## Prerequisites

- [Node.js](https://nodejs.org/): active LTS or maintenance LTS versions, currently Node.js >=18.0.0 \<=20.x.x
- npm >=6.0.0 (installed with Node.js)
- A running instance of Meilisearch (v >= 1.x). If you need help with this part, you can consult the [Installation section](/learn/self_hosted/install_meilisearch_locally).

## Create a back end using Strapi

### Set up the project

Create a directory called `my-app` where you will add the back and front-end parts of the application. Generate a back-end API using Strapi inside `my-app`:

```bash
npx create-strapi-app@latest back --quickstart
```

This command creates a Strapi app in a new directory called `back` and opens the admin dashboard. Create an account to access it.

 <img src="/assets/images/strapi-v4/strapi-signup.png" alt="Strapi sign up form" />

Once you have created your account, you should be redirected to Strapi's admin dashboard. This is where you will configure your back-end API.

### Build and manage your content

The next step is to create a new collection type. A collection is like a blueprint of your content—in this case, it will be a collection of restaurants. You will create another collection called "Category" to organize your restaurants later.

 <img src="/assets/images/strapi-v4/strapi-dashboard.png" alt="Strapi dashboard with side menu 'Content-Type Builder' option circled" />

To follow along, complete "Part B: Build your data structure with the Content-type Builder" and steps 2 to 5 in "Part D: Add content to your Strapi Cloud project with the Content Manager" from Strapi's quick start guide. These will include:

- creating collection types
- creating new entries
- setting roles & permissions
- publishing the content

### Expand your database

After finishing those steps of Strapi's quick start guide, two new collections named Restaurant and Category should have appeared under `Content Manager > Collection Types`. If you click on `Restaurant`, you can see that there is only one. Add more by clicking the `+ Create new entry` button in the upper-right corner of the dashboard.

 <img src="/assets/images/strapi-v4/strapi-restaurant-content-type.png" alt="Strapi dashboard: Content manager side menu, arrow indicating the location of the Restaurant Collection Type" />

Add the following three restaurants, one by one. For each restaurant, you need to press `Save` and then `Publish`.

- Name: `The Butter Biscotte`
- Description: `All about butter, nothing about health.`

Next, add the `French food` category on the bottom right corner of the page.

 <img src="/assets/images/strapi-v4/strapi-add-category.png" alt="Strapi dashboard: create an entry form, arrow indicating the location of the categorie's location in the right side menu" />

- Name: `The Slimy Snail`
- Description: `Gastronomy is made of garlic and butter.`
- Category: `French food`

- Name: `The Smell of Blue`
- Description: `Blue Cheese is not expired, it is how you eat it. With a bit of butter and a lot of happiness.`
- Category: `French food`

Your Strapi back-end is now up and running. Strapi automatically creates a REST API for your Restaurants collection. Check Strapi's documentation for all available [API endpoints](https://strapi.io/documentation/developer-docs/latest/developer-resources/content-api/content-api.html#api-endpoints).

Now, it’s time to connect Strapi and Meilisearch and start searching.

## Connect Strapi and Meilisearch To add the Meilisearch plugin to Strapi, you need to first quit the Strapi app. Go to the terminal window running Strapi and push `Ctrl+C` to kill the process.

Next, install the plugin in the `back` directory.

```bash
npm install strapi-plugin-Meilisearch ```

After the installation, you have to rebuild the Strapi app before starting it again in development mode, since it makes configuration easier.

```bash
npm run build
npm run develop
```

At this point, your Strapi app should be running once again on the default address: http://localhost:1337/admin. Open it in your browser. You should see an admin log-in page. Enter the credentials you used to create your account.

Once connected, you should see the new `meilisearch` plugin on the left side of the screen.

 <img src="/assets/images/strapi-v4/strapi-meilisearch-plugin.png" alt="Strapi dashboard with plugins side menu: arrow pointing at the 'meilisearch' option" />

Add your Meilisearch credentials on the Settings tab of the `meilisearch` plugin page.

 <img src="/assets/images/strapi-v4/strapi-meilisearch-credentials.png" alt="Strapi dashboard with Meilisearch plugin selected: arrow pointing to the location of the settings tab" />

Now it's time to add your Strapi collection to Meilisearch. In the `Collections` tab on the `meilisearch` plugin page, you should see the `restaurant` and `category` content-types.

By clicking on the checkbox next to `restaurant`, the content-type is automatically indexed in Meilisearch.

 <img src="/assets/images/strapi-v4/strapi-add-collection-to-meilisearch.gif" alt="GIF showing the mouse clicking on 'restaurant' in the Meilisearch collections tab" />

The word “Hooked” appears when you click on the `restaurant`'s checkbox in the `Collections` tab. This means that each time you add, update or delete an entry in your restaurant content-types, Meilisearch is automatically updated.

Once the indexing finishes, your restaurants are in Meilisearch. Access the [search preview](/learn/getting_started/search_preview) confirm everything is working correctly by searching for “butter”.

 <img src="/assets/images/strapi-v4/strapi-search-preview.gif" alt="GIF showing the word 'butter' being typed in the search bar and search results appearing instantly" />

Your Strapi entries are sent to Meilisearch as is. You can modify the data before sending it to Meilisearch, for instance by removing a field. Check out all the customization options on the [strapi-plugin-Meilisearch page](https://github.com/meilisearch/strapi-plugin-meilisearch/#-customization).

## What's next

This tutorial showed you how to add your Strapi collections to Meilisearch.

In most real-life scenarios, you'll typically build a custom search interface and fetch results using Meilisearch's API. To learn how to quickly build a front-end interface of your own, check out the [Front-end integration page](/guides/front_end/front_end_integration) guide.

---

## Integrate Cloud with Vercel

In this guide you will learn how to link a [Cloud](https://www.meilisearch.com/cloud?utm_campaign=oss&utm_source=docs&utm_medium=vercel-integration) instance to your Vercel project.

## Introducing our tools

### What is Vercel?

[Vercel](https://vercel.com/) is a cloud platform for building and deploying web applications. It works out of the box with most popular web development tools.

### What is Cloud?

[Cloud](https://www.meilisearch.com/cloud?utm_campaign=oss&utm_source=docs&utm_medium=vercel-integration) offers a managed search service i.e. scalable, reliable, and designed to meet the needs of all companies.

## Integrate Meilisearch into your Vercel project

### Create and deploy a Vercel project

From your Vercel dashboard, create a new project. You can create a project from a template, or import a Git repository.

 <img src="/assets/images/vercel/01.create-new-project-on-vercel-dashboard.png" alt="Create a new project on Vercel dashboard" />

Select your project, then click on **Deploy**. Once deployment is complete, go back to your project’s dashboard.

### Add the Meilisearch integration

Go to the project settings tab and click on **Integrations** on the sidebar menu to the left of your screen.

 <img src="/assets/images/vercel/02.project-settings-integrations-tab.png" alt="Selecting the integration tab in the project settings" />

Search for the [Meilisearch integration](https://vercel.com/integrations/meilisearch-cloud) in the search bar. Click on the **Add integration** button.

 <img src="/assets/images/vercel/03.meilisearch-cloud-integration-page-in-marketplace.png" alt="Meilisearch integration page in Vercel's marketplace" />

Select the Vercel account or team and the project you to which you want to add the integration. You may add the Meilisearch integration to one or more projects in this menu.

 <img src="/assets/images/vercel/04.add-meilisearch-cloud-form.png" alt="Form to add Meilisearch integration, the 'Specific projects' option is selected" />

Click on **Continue**. Vercel will display a list with the permissions the integration needs to work properly. Review it, then click on **Add Integration**.

### Set up Cloud

Vercel will redirect you to the Cloud page. Log in or create an account. New accounts enjoy a 14-day free trial period.

You can choose an existing project or create a new one. To create a new project, complete the form with the project name and region.

 <img src="/assets/images/vercel/05.create-a-meilisearch-cloud-project-form.png" alt="Cloud form to create a project complete, with 'search-app' as the project's name and 'Frankfurt' as the region" />

Once you click on **Create project**, you should see the following message: “Your Meilisearch + Vercel integration is one click away from being completed.” Click "Finish the Vercel integration setup". Meilisearch will then redirect you back to the Vercel integration page.

 <img src="/assets/images/vercel/06.meilisearch-cloud-integration-page-in-vercel-dashboard.png" alt="Meilisearch integration page in Vercel's dashboard" />

### Understand and use Meilisearch API keys

Meilisearch creates two default API keys: [`Default Search API Key` and `Default Admin API Key`](/learn/security/basic_security#obtaining-api-keys).

#### Admin API key

Use the `Default Admin API Key`, to control who can access or create new documents, indexes, and change index settings. Be careful with the admin key and avoid exposing it in public environments.

#### Search API key

Use the `Default Search API Key` to access the [search route](/reference/api/search). This is the one you want to use in your front end.

Both keys are automatically added to Vercel along with the Meilisearch URL.

The master key–which hasn’t been added to Vercel–grants users full control over an instance. You can find it in your project’s overview on your [Cloud dashboard](https://cloud.meilisearch.com/projects/?utm_campaign=oss&utm_source=docs&utm_medium=vercel-integration). Read more about [Meilisearch security](https://www.meilisearch.com/docs/learn/security/master_api_keys).

### Review your project settings

Go back to your project settings and check the new Meilisearch environment variables:

- `MEILISEARCH_ADMIN_KEY`
- `MEILISEARCH_URL`
- `MEILISEARCH_SEARCH_KEY`

 <img src="/assets/images/vercel/07.project-settings-environment-variables-tab.png" alt="Display the environment variables in the project settings" />

When using [Next.js](https://nextjs.org/), ensure you prefix your browser-facing environment variables with `NEXT_PUBLIC_`. This makes them available to the browser side of your application.

## Take advantage of the Cloud dashboard

 <img src="/assets/images/vercel/08.meilisearch-cloud-dashboard.png" alt="Cloud dashboard: overview of the 'search-app' project" />

Use the [Cloud dashboard](https://cloud.meilisearch.com/projects/?utm_campaign=oss&utm_source=docs&utm_medium=vercel-integration), to index documents and manage your project settings.

## Resources and next steps

Check out the [quick start guide](/learn/self_hosted/getting_started_with_self_hosted_meilisearch#add-documents) for a short introduction on how to use Meilisearch. We also provide many [SDKs and tools](/learn/resources/sdks), so you can use Meilisearch in your favorite language or framework.

You are now ready to [start searching](/reference/api/search)!

---