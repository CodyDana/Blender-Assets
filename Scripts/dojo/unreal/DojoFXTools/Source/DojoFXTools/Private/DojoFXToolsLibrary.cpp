#include "DojoFXToolsLibrary.h"

#include "NiagaraSystem.h"
#include "NiagaraRendererProperties.h"
#include "Misc/StringOutputDevice.h"
#include "UObject/UObjectHash.h"
#include "UObject/UnrealType.h"

namespace DojoFX
{
	struct FResolved
	{
		FProperty* Prop = nullptr;
		void* ValuePtr = nullptr;
		UObject* Owner = nullptr;
		FString Error;
	};

	static FResolved Resolve(UObject* Obj, const FString& Path)
	{
		FResolved R;
		if (!Obj)
		{
			R.Error = TEXT("null object");
			return R;
		}
		TArray<FString> Parts;
		Path.ParseIntoArray(Parts, TEXT("."), true);
		UStruct* Struct = Obj->GetClass();
		void* Container = Obj;
		UObject* Owner = Obj;
		for (int32 i = 0; i < Parts.Num(); ++i)
		{
			FString Name = Parts[i];
			int32 Index = INDEX_NONE;
			int32 Br = INDEX_NONE;
			if (Name.FindChar(TEXT('['), Br))
			{
				Index = FCString::Atoi(*Name.Mid(Br + 1));
				Name = Name.Left(Br);
			}
			FProperty* P = FindFProperty<FProperty>(Struct, FName(*Name));
			if (!P)
			{
				R.Error = FString::Printf(TEXT("no property %s on %s"), *Name, *Struct->GetName());
				return R;
			}
			void* Val = P->ContainerPtrToValuePtr<void>(Container);
			if (Index != INDEX_NONE)
			{
				FArrayProperty* AP = CastField<FArrayProperty>(P);
				if (!AP)
				{
					R.Error = FString::Printf(TEXT("%s is not an array"), *Name);
					return R;
				}
				FScriptArrayHelper H(AP, Val);
				if (Index < 0 || Index >= H.Num())
				{
					R.Error = FString::Printf(TEXT("%s index %d out of %d"), *Name, Index, H.Num());
					return R;
				}
				P = AP->Inner;
				Val = H.GetRawPtr(Index);
			}
			if (i == Parts.Num() - 1)
			{
				R.Prop = P;
				R.ValuePtr = Val;
				R.Owner = Owner;
				return R;
			}
			if (FStructProperty* SP = CastField<FStructProperty>(P))
			{
				Struct = SP->Struct;
				Container = Val;
			}
			else if (FObjectPropertyBase* OP = CastField<FObjectPropertyBase>(P))
			{
				UObject* Sub = OP->GetObjectPropertyValue(Val);
				if (!Sub)
				{
					R.Error = FString::Printf(TEXT("%s is null"), *Name);
					return R;
				}
				Struct = Sub->GetClass();
				Container = Sub;
				Owner = Sub;
			}
			else
			{
				R.Error = FString::Printf(TEXT("cannot walk into %s"), *Name);
				return R;
			}
		}
		R.Error = TEXT("empty path");
		return R;
	}
}

TArray<FString> UDojoFXToolsLibrary::ListInner(UObject* Root)
{
	TArray<FString> Out;
	if (!Root)
	{
		return Out;
	}
	TArray<UObject*> Objs;
	GetObjectsWithOuter(Root, Objs, true);
	for (UObject* O : Objs)
	{
		Out.Add(O->GetPathName() + TEXT("|") + O->GetClass()->GetName());
	}
	return Out;
}

UObject* UDojoFXToolsLibrary::FindInner(UObject* Root, const FString& ClassName, const FString& NameContains)
{
	if (!Root)
	{
		return nullptr;
	}
	TArray<UObject*> Objs;
	GetObjectsWithOuter(Root, Objs, true);
	for (UObject* O : Objs)
	{
		if (O->GetClass()->GetName() == ClassName && (NameContains.IsEmpty() || O->GetName().Contains(NameContains)))
		{
			return O;
		}
	}
	return nullptr;
}

TArray<FString> UDojoFXToolsLibrary::ListProps(UObject* Obj)
{
	TArray<FString> Out;
	if (!Obj)
	{
		return Out;
	}
	for (TFieldIterator<FProperty> It(Obj->GetClass()); It; ++It)
	{
		FString V;
		It->ExportTextItem_Direct(V, It->ContainerPtrToValuePtr<void>(Obj), nullptr, Obj, PPF_None);
		Out.Add(It->GetName() + TEXT("|") + It->GetCPPType() + TEXT("|") + V.Left(3000));
	}
	return Out;
}

FString UDojoFXToolsLibrary::GetProp(UObject* Obj, const FString& Path)
{
	DojoFX::FResolved R = DojoFX::Resolve(Obj, Path);
	if (!R.Prop)
	{
		return TEXT("ERR ") + R.Error;
	}
	FString V;
	R.Prop->ExportTextItem_Direct(V, R.ValuePtr, nullptr, R.Owner, PPF_None);
	return V;
}

FString UDojoFXToolsLibrary::SetProp(UObject* Obj, const FString& Path, const FString& Value)
{
	DojoFX::FResolved R = DojoFX::Resolve(Obj, Path);
	if (!R.Prop)
	{
		return R.Error;
	}
	R.Owner->Modify();
	FStringOutputDevice Err;
	const TCHAR* Res = R.Prop->ImportText_Direct(*Value, R.ValuePtr, R.Owner, PPF_None, &Err);
	if (!Res)
	{
		return FString::Printf(TEXT("ImportText failed for %s: %s"), *Path, *Err);
	}
	if (!Err.IsEmpty())
	{
		return FString::Printf(TEXT("ImportText warning for %s: %s"), *Path, *Err);
	}
	return FString();
}

UObject* UDojoFXToolsLibrary::ReplaceArrayWithNew(UObject* Obj, const FString& ArrayName, UClass* NewClass)
{
	if (!Obj || !NewClass)
	{
		return nullptr;
	}
	FArrayProperty* AP = FindFProperty<FArrayProperty>(Obj->GetClass(), FName(*ArrayName));
	FObjectPropertyBase* Inner = AP ? CastField<FObjectPropertyBase>(AP->Inner) : nullptr;
	if (!Inner || !NewClass->IsChildOf(Inner->PropertyClass))
	{
		return nullptr;
	}
	Obj->Modify();
	UObject* New = NewObject<UObject>(Obj, NewClass, NAME_None, RF_Transactional);
	FScriptArrayHelper H(AP, AP->ContainerPtrToValuePtr<void>(Obj));
	H.EmptyValues();
	const int32 I = H.AddValue();
	Inner->SetObjectPropertyValue(H.GetRawPtr(I), New);
	return New;
}

FString UDojoFXToolsLibrary::FinalizeSystem(UNiagaraSystem* System)
{
	if (!System)
	{
		return TEXT("null system");
	}
	TArray<UObject*> Objs;
	GetObjectsWithOuter(System, Objs, true);
	int32 NR = 0, NM = 0, NE = 0;
	for (UObject* O : Objs)
	{
		if (O->IsA<UNiagaraRendererProperties>())
		{
			O->PostEditChange();
			++NR;
		}
	}
	for (UObject* O : Objs)
	{
		if (O->GetClass()->GetName().StartsWith(TEXT("NiagaraStatelessModule")))
		{
			O->PostEditChange();
			++NM;
		}
	}
	for (UObject* O : Objs)
	{
		const FString CN = O->GetClass()->GetName();
		if (CN == TEXT("NiagaraStatelessEmitter") || CN == TEXT("NiagaraEmitter"))
		{
			O->PostEditChange();
			++NE;
		}
	}
	System->PostEditChange();
	const bool bReq = System->RequestCompile(false);
	System->WaitForCompilationComplete(false, false);
	System->MarkPackageDirty();
	return FString::Printf(TEXT("renderers=%d modules=%d emitters=%d compile_requested=%d valid=%d"), NR, NM, NE,
		bReq ? 1 : 0, System->IsValid() ? 1 : 0);
}
