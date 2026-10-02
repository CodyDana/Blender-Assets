#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DojoFXToolsLibrary.generated.h"

class UNiagaraSystem;

UCLASS()
class UDojoFXToolsLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** Every object whose outer chain reaches Root, as "PathName|ClassName". */
	UFUNCTION(BlueprintCallable, Category = "Dojo|FX")
	static TArray<FString> ListInner(UObject* Root);

	/** The first object inside Root (outer chain) whose class name equals ClassName and, if NameContains is not empty,
	 *  whose object name contains it. */
	UFUNCTION(BlueprintCallable, Category = "Dojo|FX")
	static UObject* FindInner(UObject* Root, const FString& ClassName, const FString& NameContains);

	/** Every reflected property of Obj as "Name|CPPType|ExportText" (top level only). */
	UFUNCTION(BlueprintCallable, Category = "Dojo|FX")
	static TArray<FString> ListProps(UObject* Obj);

	/** ExportText of the property at Path ("A", "A.B", "A[2].B"; struct members, array elements and object references
	 *  are walked). Returns "ERR ..." when the path does not resolve. */
	UFUNCTION(BlueprintCallable, Category = "Dojo|FX")
	static FString GetProp(UObject* Obj, const FString& Path);

	/** ImportText of Value into the property at Path (see GetProp). Calls Modify() first. Returns "" on success, else the
	 *  reason. */
	UFUNCTION(BlueprintCallable, Category = "Dojo|FX")
	static FString SetProp(UObject* Obj, const FString& Path, const FString& Value);

	/** Empties the object array property ArrayName on Obj and adds one new object of NewClass (outer = Obj). */
	UFUNCTION(BlueprintCallable, Category = "Dojo|FX")
	static UObject* ReplaceArrayWithNew(UObject* Obj, const FString& ArrayName, UClass* NewClass);

	/** PostEditChange on every object inside the system (renderers and modules first, emitters last), then a system
	 *  compile (RequestCompile + WaitForCompilationComplete) and MarkPackageDirty. Returns a short report. */
	UFUNCTION(BlueprintCallable, Category = "Dojo|FX")
	static FString FinalizeSystem(UNiagaraSystem* System);
};
