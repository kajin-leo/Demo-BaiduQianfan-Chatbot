[中文](#zh)|[英文](#en)
<p id="zh"></p>

# 中文Readme
这个Demo是基于`LangChain`和百度千帆模型搭建的聊天机器人，其中兼顾了Completion模式与RAG模式。Demo来源于作者在实习时做的任务，基于公司Wiki库回答用户提问的聊天机器人。

`LangChain`有利于Demo向不同的大型语言模型进行改造，在参考[LangChain官方Tutorial](https://python.langchain.com/v0.2/docs/tutorials/retrievers/)的情况下可以通过较少量的修改来实现。另外，在Demo中使用了`Flask`库进行包装，以便响应网络请求。

## 附加文件说明
项目的虚拟环境为`.venv`目录，在`.venv`目录下会有一个名为`hash.json`的文件以及一个`data`文件夹。`hash.json`文件是用于实现RAG模式的知识库增量上传的辅助文件。`data`文件夹下存有知识库数据源的`.csv`文件。

目前Demo中只使用了`CSVLoader`来读取知识库，如果有需要的其他格式，可以参考[LangChain的Loader介绍](https://python.langchain.com/v0.2/docs/how_to/#document-loaders)进行添加和修改。

## 通过网络请求与接口交互
由于作者的实习单位主要使用PHP语言，作者也对B/S开发经验不足，这里只提供PHP语言的参考脚本。
### 清理数据库与检查数据库内数据量
```php
function callChatBotAPI($operation){ //$operation是clear或check
    $url = "http://localhost:8204/chatbot/{$operation}";
    $options = array(
        'http' => array(
            'header' => 'Content-type: application/json\r\n',
            'method' => 'POST'
        )
    );
    $context = stream_context_create($options);
    $result = file_get_contents($url, false, $context);
    if ($result === FALSE) {
        throw new Exception('Failed to interact with chatbot');
    }
    if ($operation == 'check') {
        return json_decode($result, true)["library_name"] . json_decode($result, true)["library_count"];
    }
    return json_decode($result, true)['output'];
}
```

### 上传知识库
```php
function callChatBotAPI(){
    $url = 'http://localhost:8204/chatbot/upload';
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_WRITEFUNCTION, function ($curl, $data) {
        $output = json_decode($data, true)["output"];
        echo "{$output}\n";
        return strlen($data);
    });
    curl_exec($ch);
    curl_close($ch);
}
```

### Wiki与Completion模式
```php
function callChatBotAPI($operation, $content){ //$operation是wiki或completion
    $ch = curl_init($url);
    $context = json_encode(array('content' => $content));
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $context);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Accept: text/event-stream'
    ]);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_WRITEFUNCTION, function ($curl, $data) {
        $output = json_decode($data, true);
        if($output != null && $output["status"] == "active") {
            echo "{$output["output"]}";
        }
        return strlen($data);
    });
    curl_exec($ch);
    curl_close($ch);
}
```

<p id="en"></p>

# English Readme
This demo is a ChatBot based on `LangChain` and BaiduQianfan LLM, which contains both Completion mode and RAG mode. The Demo was originated from a task during the internship of the author, which was to construct a ChatBot based on the Wiki Library of the company. 

`LangChain` makes it much easier to modify for different LLM models. With the help of [LangChain Official Tutorial](https://python.langchain.com/v0.2/docs/tutorials/retrievers/), it's possible to change the demo to other LLMs through only a little bit of codings. Additionally, 'Flask' was used to pack the demo for responding to HTTP Requests. 

## Descriptions for Additional Files
There is a directory called `.venv` to work as the virtual environment, containing a file named as `hash.json` and a directory named as `data`. `hash.json` is used to assist with uploading the wiki library incrementally. `data` directory stores wiki library files in `.csv` filename extension. 
So far, the demo only imports and uses `CSVLoader` to load the wiki library. If any other file format is needed, you can take [LangChain Loaders Introduction](https://python.langchain.com/v0.2/docs/how_to/#document-loaders) as reference to modify the demo. 

## Using HTTP Requests
Since the author is not familiar with B/S developing and PHP was mainly used in the company where the author had internship, all the following referral scripts are wrote in PHP. 
### Clear Up the Vector Database & Check the Vector Database
```php
function callChatBotAPI($operation){ //$operation should only be in 'clear' or 'check'
    $url = "http://localhost:8204/chatbot/{$operation}";
    $options = array(
        'http' => array(
            'header' => 'Content-type: application/json\r\n',
            'method' => 'POST'
        )
    );
    $context = stream_context_create($options);
    $result = file_get_contents($url, false, $context);
    if ($result === FALSE) {
        throw new Exception('Failed to interact with chatbot');
    }
    if ($operation == 'check') {
        return json_decode($result, true)["library_name"] . json_decode($result, true)["library_count"];
    }
    return json_decode($result, true)['output'];
}
```

### Upload Wiki Library
```php
function callChatBotAPI(){
    $url = 'http://localhost:8204/chatbot/upload';
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_WRITEFUNCTION, function ($curl, $data) {
        $output = json_decode($data, true)["output"];
        echo "{$output}\n";
        return strlen($data);
    });
    curl_exec($ch);
    curl_close($ch);
}
```

### Chat using Wiki & Completion Modes
```php
function callChatBotAPI($operation, $content){ //$operation should only be in 'wiki' or 'completion'
    $ch = curl_init($url);
    $context = json_encode(array('content' => $content));
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $context);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Accept: text/event-stream'
    ]);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_WRITEFUNCTION, function ($curl, $data) {
        $output = json_decode($data, true);
        if($output != null && $output["status"] == "active") {
            echo "{$output["output"]}";
        }
        return strlen($data);
    });
    curl_exec($ch);
    curl_close($ch);
}
```
